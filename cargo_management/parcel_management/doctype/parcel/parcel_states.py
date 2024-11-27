from enum import StrEnum

import frappe


class Status(StrEnum):
	""" Parcel Doctype Statuses """
	AWAITING_RECEIPT = 'Awaiting Receipt'
	AWAITING_CONFIRMATION = 'Awaiting Confirmation'
	IN_EXTRAORDINARY_CONFIRMATION = 'In Extraordinary Confirmation'  # FIXME: We can remove "IN"
	AWAITING_DEPARTURE = 'Awaiting Departure'
	IN_TRANSIT = 'In Transit'
	IN_CUSTOMS = 'In Customs'
	SORTING = 'Sorting'
	TO_BILL = 'To Bill'
	UNPAID = 'Unpaid'
	FOR_DELIVERY_OR_PICKUP = 'For Delivery or Pickup'  # FIXME, we can make to DELIVERY_OR_PICKUP
	FINISHED = 'Finished'
	CANCELLED = 'Cancelled'
	NEVER_ARRIVED = 'Never Arrived'
	RETURNED_TO_SENDER = 'Returned to Sender'


class ParcelState:
	"""Base State class that also manages transitions and explanations."""
	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from apps.cargo_management.cargo_management.parcel_management.doctype.parcel.parcel import Parcel

	parcel: 'Parcel'
	color: str = 'blue'

	def __init__(self, parcel: 'Parcel'):
		self.parcel = parcel

	def explain_state(self) -> tuple[list[str], str]:
		raise NotImplementedError

	@staticmethod
	def create_state(status: str, parcel: 'Parcel') -> 'ParcelState':
		"""Factory method to create ParcelState instances based on the current status."""
		state_classes = {
			Status.AWAITING_RECEIPT: AwaitingReceipt,
			Status.AWAITING_CONFIRMATION: AwaitingConfirmation,
			Status.IN_EXTRAORDINARY_CONFIRMATION: InExtraordinaryConfirmation,
			Status.AWAITING_DEPARTURE: AwaitingDeparture,
			Status.IN_TRANSIT: InTransit,
			Status.IN_CUSTOMS: InCustoms,
			Status.SORTING: Sorting,
			Status.TO_BILL: ToBill,
			Status.UNPAID: Unpaid,
			Status.FOR_DELIVERY_OR_PICKUP: ForDeliveryOrPickup,
			Status.FINISHED: Finished,
			Status.CANCELLED: Cancelled,
			Status.NEVER_ARRIVED: NeverArrived,
			Status.RETURNED_TO_SENDER: ReturnedToSender
		}

		return state_classes.get(status)(parcel)


class AwaitingReceipt(ParcelState):
	def explain_state(self):
		message = ['<p>El paquete aún no ha sido marcado como entregado por el transportista.</p>']

		if self.parcel.carrier_est_delivery:  # The carrier has provided an estimated delivery date
			est_delivery_diff = frappe.utils.date_diff(None, self.parcel.carrier_est_delivery)  # Diff from estimated to today
			est_delivery_date = frappe.utils.format_date(self.parcel.carrier_est_delivery, 'medium')  # readable date

			if est_delivery_diff == 0:  # Delivery is today
				message.append('La fecha programada de entrega es: <b>hoy.</b>')
			elif est_delivery_diff == -1:  # Delivery is tomorrow
				message.append('La fecha programada es para <b>mañana.</b>')
			elif est_delivery_diff < 0:  # Delivery is in the next days
				message.append(f'La fecha programada es: {est_delivery_date}')
			else:  # Delivery is late
				self.color = 'pink'
				message.append(f'Esta retrasado. Debio de ser entregado el: {est_delivery_date}')
				message.append('Contacte a su proveedor para obtener mas información.')
		else:
			self.color = 'yellow'
			message.append('<b>No se ha indicado una fecha de entrega estimada.</b>')

		return message, self.color


class AwaitingConfirmation(ParcelState):
	def explain_state(self):
		if self.parcel.carrier_real_delivery:
			message = ['El transporte indica que entregó el: {0}'.format(
				frappe.utils.format_datetime(self.parcel.carrier_real_delivery, "EEEE, d 'de' MMMM yyyy 'a las' h:mm a").capitalize()
			)]

			if self.parcel.signed_by:
				message.append('Signed By: {}'.format(self.parcel.signed_by))

			# TODO: check against current user tz: Change None to now in local delivery place timezone
			delivered_since = frappe.utils.time_diff(None, self.parcel.carrier_real_delivery)  # datetime is UTC

			# TODO: Compare Against Workable days
			# Parcel has exceeded the 24 hours timespan to be confirmed. Same as: time_diff_in_hours() >= 24.00
			if delivered_since.days >= 1:  # The day starts counting after 1-minute difference
				self.color = 'red'

				delivered_since_str = 'Ha pasado 1 día' if delivered_since.days == 1 else 'Han pasado {} días'

				message.append(delivered_since_str.format(delivered_since.days))
			else:
				message.append('Por favor espera 24 horas hábiles para que el almacén confirme la recepción.')
		elif self.parcel.carrier_est_delivery:
			self.color = 'yellow'
			message = ['El transportista INDICO una fecha de entrega aproximada: {}'.format(
				frappe.utils.format_datetime(self.parcel.carrier_est_delivery, 'medium')
			)]
		else:
			self.color = 'yellow'
			message = ['No se ha indicado una fecha de entrega estimada', 'Contacte a su proveedor para obtener mas información.']

		return message, self.color


class InExtraordinaryConfirmation(AwaitingConfirmation):
	def explain_state(self):
		[messages, color] = super().explain_state()
		messages.append('El paquete se encuentra siendo verificado de forma extraordinaria.')

		return messages, color


class AwaitingDeparture(ParcelState):
	def explain_state(self):
		message = []
		# TODO: Add Warehouse Receipt date

		if self.parcel.carrier_real_delivery:
			message.append('El transportista indica que entrego el paquete el: {}'.format(
				frappe.utils.format_datetime(self.parcel.carrier_real_delivery, 'medium'))
			)
		if self.parcel.signed_by:
			message.append('Firmado por: {0}'.format(self.parcel.signed_by))

		if self.parcel.cargo_shipment:  # TODO: Add cargo shipment calendar
			message.append('Embarque: {}'.format(self.parcel.cargo_shipment))
			message.append('Fecha esperada de recepcion en Managua: {}'.format(
				frappe.get_cached_value('Cargo Shipment', self.parcel.cargo_shipment, 'expected_arrival_date')
			))  # FIXME: Improve Performance!

		return message, self.color


class InTransit(ParcelState):
	def explain_state(self):
		if not self.parcel.cargo_shipment:
			return ['No hay envio de carga'], 'red'

		cargo_shipment = frappe.get_cached_doc('Cargo Shipment', self.parcel.cargo_shipment)  # FIXME: Performance!
		return [
			'El paquete esta en transito a destino. Via: {0}'.format(cargo_shipment.transportation),
			'Fecha de despacho: {0}'.format(cargo_shipment.departure_date),
			'Fecha esperada de recepcion en Managua: {0}'.format(cargo_shipment.expected_arrival_date),
			'Embarque: {0}'.format(self.parcel.cargo_shipment)
		], 'purple'


class InCustoms(ParcelState):
	def explain_state(self):
		return ['El paquete se encuentra en proceso de desaduanaje.'], 'gray'


class Sorting(ParcelState):
	def explain_state(self):
		return ['El paquete se encuentra siendo clasificado en oficina.'], 'blue'


class ToBill(ParcelState):
	def explain_state(self):
		return ['El paquete esta listo para ser Cobrado?.'], 'green'


class Unpaid(ParcelState):
	def explain_state(self):
		return ['El paquete esta listo para ser retirado.'], 'green'


class ForDeliveryOrPickup(ParcelState):
	def explain_state(self):
		return ['El paquete esta listo para ser entregado o retirado.'], 'green'


class Finished(ParcelState):
	# TODO: Show invoice, delivery and payment details.
	def explain_state(self):
		return ['El paquete ha sido entregado satisfactoriamente.'], 'green'


class Cancelled(ParcelState):
	def explain_state(self):
		return ['Contáctese con un agente para obtener mayor información del paquete.'], 'orange'


class NeverArrived(ParcelState):
	def explain_state(self):
		return [
			'El paquete no llego al almacén.',
			'Contáctese con su vendedor y/o transportista para obtener mayor información.'
		], 'red'


class ReturnedToSender(ParcelState):
	def explain_state(self):
		return [
			'El paquete fue devuelto por el transportista al vendedor.'
			'Contáctese con su vendedor y/o transportista para obtener mayor información.'
		], 'red'


class ParcelStateMachine:
	# Base class for all states
	def __init__(self, status=Status.AWAITING_RECEIPT):
		self.state = status

	def _allowed_transition(self, value, allowed_statuses: any) -> bool:
		if value in allowed_statuses:
			self.state = value
			return True
		else:
			return False

	def transition(self, event: Status) -> bool:
		match self.state:
			case Status.AWAITING_RECEIPT:
				return self._allowed_transition(event, [Status.AWAITING_CONFIRMATION, Status.RETURNED_TO_SENDER, Status.AWAITING_DEPARTURE, Status.SORTING])
			case Status.AWAITING_CONFIRMATION:
				return self._allowed_transition(event, [Status.AWAITING_DEPARTURE, Status.SORTING])
			case Status.IN_EXTRAORDINARY_CONFIRMATION:
				return self._allowed_transition(event, [Status.AWAITING_DEPARTURE, Status.SORTING])
			case Status.AWAITING_DEPARTURE:
				return self._allowed_transition(event, [Status.IN_TRANSIT, Status.SORTING])
			case Status.IN_TRANSIT:
				return self._allowed_transition(event, [Status.SORTING])
			case Status.FOR_DELIVERY_OR_PICKUP:
				return self._allowed_transition(event, [Status.TO_BILL])
			case Status.FINISHED:
				return self._allowed_transition(event, [Status.TO_BILL])
			case Status.TO_BILL:
				return self._allowed_transition(event, [Status.TO_BILL])
			case _:
				return False

# constants reverts: 62e4deb
# utils reverts: 863fa2a
# TODO: 55 + 340(parcel.py) = 395
# 69 Lineas Por aca
# 225 Lineas y Funcionando all 100%.

# frappe.local.lang = LocaleLanguage.SPANISH  # FIXME: Little Hack ? # TODO: I18N Translate!

# 3 3 90 = Empezando a Crear Templates de Respuesta | 243

