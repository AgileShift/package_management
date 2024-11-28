from typing import override

from easypost.errors.api import ApiError as EasyPostAPIError

import frappe
from frappe import _
from frappe.model.document import Document
from .api.api_17track import API17Track
from .api.easypost_api import EasyPostAPI
from .parcel_states import Status, ParcelState


class Parcel(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from cargo_management.parcel_management.doctype.parcel_content.parcel_content import ParcelContent
		from frappe.types import DF

		assisted_purchase: DF.Check
		cargo_shipment: DF.Link | None
		carrier: DF.Literal["Drop Off", "Pick Up", "Unknown", "Amazon", "USPS", "UPS", "DHL", "FedEx", "OnTrac", "Cainiao", "SF Express", "Yanwen", "YunExpress", "SunYou", "Pitney Bowes", "Veho"]
		carrier_est_delivery: DF.Datetime | None
		carrier_est_weight: DF.Float
		carrier_last_detail: DF.SmallText | None
		carrier_real_delivery: DF.Datetime | None
		carrier_status: DF.Literal["Unknown", "Pre Transit", "In Transit", "Out For Delivery", "Available For Pickup", "Delivered", "Return To Sender", "Failure", "Cancelled", "Error"]
		carrier_status_detail: DF.Data | None
		content: DF.Table[ParcelContent]
		customer: DF.Link | None
		customer_name: DF.Data | None
		easypost_id: DF.Data | None
		est_delivery_1: DF.Date | None
		est_delivery_2: DF.Date | None
		est_departure: DF.Date | None
		explained_status: DF.Data | None
		has_taxes: DF.Check
		notes: DF.SmallText | None
		order_date: DF.Date | None
		order_number: DF.Data | None
		residential_address: DF.Check
		shipper: DF.Link | None
		shipping_amount: DF.Currency
		signed_by: DF.Data | None
		status: DF.Literal["Awaiting Receipt", "Awaiting Confirmation", "In Extraordinary Confirmation", "Awaiting Departure", "In Transit", "In Customs", "Sorting", "To Bill", "Unpaid", "For Delivery or Pickup", "Finished", "Cancelled", "Never Arrived", "Returned to Sender"]
		sub_status: DF.Literal["At Origin", "Delayed"]
		total: DF.Currency
		tracking_number: DF.Data
		transportation: DF.Literal["Sea", "Air"]
	# end: auto-generated types
	"""  All these are Frappe Core Flags:
		'ignore_links':       avoid: _validate_links()
		'ignore_validate':    avoid: validate() and before_save()
		'ignore_mandatory':   avoid: _validate_mandatory()
		'ignore_permissions': avoid: will not check for permissions globally.
	"""

	@override
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		print('parcel.py')
		print(self.tracking_number)
		print(self.status)

		self.state = ParcelState.create_state(self, self.status)  # Creating the State Object from Factory Method

	@override
	def save(self, request_data_from_api=False, *args, **kwargs):
		""" Override def to change validation behaviour. Useful when called from outside a form. """
		if request_data_from_api:  # If True we fetch data from API, ignore ALL checks and save it.
			self.flags.ignore_permissions = self.flags.ignore_validate = self.flags.ignore_mandatory = self.flags.ignore_links = True
			self.request_data_from_api()

		return super(Parcel, self).save(*args, **kwargs)

	def validate(self):
		""" Sanitize fields """
		self.tracking_number = self.tracking_number.strip().upper()  # Only uppercase with no spaces

	def before_save(self):
		""" Before saved in DB and after validated. Add new data. This runs on Insert(Create) or Save(Update)"""
		if self.is_new():
			self.request_data_from_api()
			# TODO: WORK ON THIS CHANGE!
		elif self.has_value_changed('carrier') or self.has_value_changed('tracking_number'):  # Exists and data has changed
			self.easypost_id = None  # Value has changed. We reset the ID. FIXME: Move this when we have new APIs.
			self.request_data_from_api()
			frappe.msgprint("Carrier or Tracking Number has changed, we have requested new data.", indicator='yellow', alert=True)

	def change_status(self, new_status: Status) -> bool:
		"""
		Validates the current status of the parcel and change it if it's possible.

		# Parcel was waiting for receipt, now is mark as delivered. waiting for confirmation.
		# Parcel was waiting for receipt or confirmation and now is waiting for the departure.
		# Parcel was not received and not confirmed, but has appear on the warehouse receipt.

		# TODO: Validate this when status is changed on Form-View or List-View
		"""
		if (self.status != new_status and
			(self.status == 'Awaiting Receipt' and new_status in ['Awaiting Confirmation', 'Returned to Sender']) or
			(self.status in ['Awaiting Receipt', 'Awaiting Confirmation', 'In Extraordinary Confirmation', 'Cancelled'] and new_status == 'Awaiting Departure') or
			(self.status == 'Awaiting Departure' and new_status == 'In Transit') or
			(self.status in ['Awaiting Receipt', 'Awaiting Confirmation', 'In Extraordinary Confirmation', 'Awaiting Departure', 'In Transit', 'Cancelled'] and new_status == 'Sorting') or
			(self.status not in ['Unpaid', 'For Delivery or Pickup', 'Finished'] and new_status == 'To Bill') or
			(self.status in ['Sorting', 'To Bill'] and new_status == 'Unpaid') or
			(self.status == 'Unpaid' and new_status == 'For Delivery or Pickup')):
			self.status = new_status
			return True

		frappe.throw('Cannot Change Status of Parcel: {}'.format(self.name))  # TODO: Move this to Parcel State Machine

	@property
	def explained_status(self):
		""" This returns a detailed explanation of the current status of the Parcel. """
		message, color = self.state.explain_state()
		return {'message': message, 'color': color}

	def request_data_from_api(self):
		""" This selects the corresponding API to request data. Using Polymorphism. """
		carrier_api = frappe.get_file_json(frappe.get_app_path('Cargo Management', 'public', 'carriers.json'))['CARRIERS'].get(self.carrier, {}).get('api')

		match carrier_api:
			case 'EasyPost':
				api_data = self._request_data_from_easypost_api()
			case '17Track':
				api_data = self._request_data_from_17track_api()
			case _:
				frappe.msgprint(_('Parcel is handled by a carrier we can\'t track.'), indicator='red', alert=True)
				return

		if not api_data:  # HOTFIX: We should always return something?
			return  # If we don't return, the try will fail, and api_data.get will raise a big error(None has not .get())

		try:
			self.update_from_api_data(api_data)  # Data from API that will be saved
			frappe.msgprint(_('Parcel has been updated from {} API.').format(carrier_api), indicator='green', alert=True)
		except Exception as e:
			frappe.log_error(f"API Error: {type(e).__name__} -> {e}", reference_doctype='Parcel', reference_name=api_data.get('data', {}).get('number', None))

	def _request_data_from_easypost_api(self) :
		""" Handles POST or GET to the Easypost API. Also parses the data. """
		try:
			if self.easypost_id:  # Parcel exists on Database. Request updates from API.
				return EasyPostAPI(self.carrier).retrieve_package_data(self.easypost_id)
			else:  # Parcel don't exist on System or EasyPost. We create a new one and attach it.
				return EasyPostAPI(self.carrier).register_package(self.tracking_number)
		except EasyPostAPIError as e:
			frappe.msgprint(msg=str(e.__dict__), title='EasyPost API Error', raise_exception=False, indicator='red')

	# FIXME: 6 - 10 - 81
	def _request_data_from_17track_api(self):
		try:
			if self.easypost_id:
				return API17Track(self.carrier).retrieve_package_data(self.tracking_number)
			else:
				api_data = API17Track(self.carrier).register_package(self.tracking_number)
				self.easypost_id = api_data['tag']  # api_data.get('tag', frappe.generate_hash(length=10))
				return api_data
		except Exception as e:
			frappe.msgprint(msg=str(e), title='17Track API Error', raise_exception=False, indicator='red')
			return None  # HOTFIX for "if not api_data:"

	def update_from_api_data(self, api_data: dict) -> None:
		""" This updates the parcel with the data from the API. """
		self.__dict__.update(api_data)  # Updating all the DICT to the Parcel DocType

		if api_data['carrier_status'] == 'Delivered':  # or api_data['carrier_status_detail'] == 'Arrived At Destination':
			self.change_status(Status.AWAITING_CONFIRMATION)
		elif api_data['carrier_status'] == 'Return To Sender' or self.carrier_status_detail == 'Return':
			self.change_status(Status.RETURNED_TO_SENDER)
		else:  # TODO: Change the status when the carrier status: failure, cancelled, error
			self.change_status(Status.AWAITING_RECEIPT)

# 294(HOTFIX) -> 250(WORKING) FIXME: Better way to update the doc: create some core method that returns a Object that we can concat :D
# 248 EasyPost DONE, Now 17 Track -> 238(Production | We need to avoid extra 'try')
# 241: Retornanos data normalizada desde las API, ahora debemos de hacer Polymorphism to select the API's

# FIXME: 19 warning, 20 w warning, 83 typos -> 287
# FIXME: 2 warning, 20 w warning, 85 typos -> 276
# 292 Refactor de constantes y estados
# FIXME 311: 2 warning, 29 w warning, 21 typos -> 276 | Corregir State Machine y COLOR usage!
# FIXME 313: 9 Warning, 29 w warning, 22 typos -> 303 | Corregir State Machine y Color Usage!
# TODO: 306 -> State Design Pattern -> Utils file plus Parcel States, and explained status message not working!
# 197 -> A punto de integrar el MachineState con el State
