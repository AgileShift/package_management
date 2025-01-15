import re
from datetime import datetime as dt
from types import SimpleNamespace

from requests import post

import frappe
from frappe.app import handle_exception


class API17Track:
	API_BASE: str = "https://api.17track.net/track/v2.2/"

	# The Dict Keys are the actual String representation for Users, and the Dict Values are the carrier code for the API
	# See More at: https://res.17track.net/asset/carrier/info/apicarrier.all.json
	CARRIER_CODES: dict = {
		'Amazon': 100143,  # Swiship it works
		'FedEx': 100003,
		'OnTrac': 100049,
		'Cainiao': 190271,
		'SF Express': 190766,  # or: 100012 for intl
		'Yanwen': 190012,
		'YunExpress': 190008,
		'SunYou': 190072,
		'Pitney Bowes': 100036,
		'SpeedX': 190844,
	}

	# See List of status at: https://api.17track.net/en/doc?anchor=main-status-of-the-shipping-process&version=v2
	STATUSES: dict = {
		'Not Found': 'Unknown',
		'Info Received': 'Pre Transit',
		'Expired': 'Failure', 'Delivery Failure': 'Failure',
		'Exception': 'Error'
	}

	SUB_STATUS_TO_STATUS: dict = {  # This Map 17Track SubStatus to Statuses
		'Exception Returning': 'Return To Sender', 'Exception Returned': 'Return To Sender',
		'Exception Cancel': 'Cancelled'
	}

	# 17Track Error Codes: https://api.17track.net/en/doc?anchor=list-of-error-codes&version=v2
	TRACKING_REGISTERED = -18019901
	TRACKING_NEED_REGISTER = -18019902
	QUOTA_LIMIT = -18019908

	def __init__(self, carrier: str) -> None:
		self.data = {}
		self.carrier = self.CARRIER_CODES.get(carrier)  # Fail Silently?
		self.api_key = frappe.conf['17track_api_key']

	@staticmethod
	def unscrub(txt: str) -> str:
		""" Converts: OutForDelivery to Out For Delivery """
		return ' '.join(re.findall('[A-Z][a-z]*', txt))

	def _build_request(self, endpoint: str, payload: list):
		response = post(url=f"{self.API_BASE + endpoint}", json=payload, headers={
			"content-type": "application/json",
			"17token": self.api_key
		}).json(object_hook=lambda d: SimpleNamespace(**d)).data  # Convert to Object and return the 'data' key

		if response.accepted:
			return response.accepted[0]

		match response.rejected[0].error.code:
			case self.TRACKING_REGISTERED | self.TRACKING_NEED_REGISTER:
				raise Exception(response.rejected[0].error.message)  # Default Throw
			case self.QUOTA_LIMIT | _:
				raise Exception(response.rejected[0].error)

	def register_package(self, tracking_number: str):
		""" Register a Tracking on 17Track """
		unique_tag = frappe.generate_hash(tracking_number, length=15)

		creation = self._build_request('register', payload=[{
			"number": tracking_number,
			"carrier": self.carrier,
			"tag": unique_tag,  # CUSTOM: With this we know if the Parcel has been created on 17Track API
			"auto_detection": False,  # So we avoid sending the carrier?
		}])

		# FIXME: QUICK HACK!, maybe will not work

		return self.retrieve_package_data(tracking_number)  # Update the Parcel Data (Status, etc

	def retrieve_package_data(self, tracking_number: str) -> dict:
		""" Retrieve data from 17Track Tracking """
		obj_17track = self._build_request('gettrackinfo', payload=[{
			"number": tracking_number
		}])

		return self._build_parcel_data(obj_17track.track_info)

	def convert_from_webhook(self, response):
		""" Convert a dict from 17Track to our Parcel Object. """
		obj_17track = SimpleNamespace(**response)
		obj_17track.latest_status = SimpleNamespace(**response['latest_status'])

		obj_17track.latest_event = SimpleNamespace(**response['latest_event'])
		obj_17track.latest_event.address = SimpleNamespace(**response['latest_event']['address'])

		obj_17track.misc_info = SimpleNamespace(**response['misc_info'])

		obj_17track.time_metrics = SimpleNamespace(**response['time_metrics'])
		obj_17track.time_metrics.estimated_delivery_date = SimpleNamespace(**response['time_metrics']['estimated_delivery_date'])

		return self._build_parcel_data(obj_17track)

	def _build_parcel_data(self, obj_17track) -> dict:
		""" Build our Object(Parcel Document) from 17Track Data. """
		self.data: dict = {
			'carrier_status': self.STATUSES.get(stat := self.unscrub(obj_17track.latest_status.status), stat),  # Unscrub
			'carrier_status_detail': self.unscrub(obj_17track.latest_status.sub_status),               # Normalize SubStatus
			'carrier_est_weight': round(float(obj_17track.misc_info.weight_kg or 0.00) * 2.20462, 1),  # From KG to Pounds
		}

		# Change 'status' if the 'status_detail' gives us more information about it!
		if self.data['carrier_status'] == 'Error':  # Originally 'Exception'. See STATUS_MAP
			self.data['carrier_status'] = self.SUB_STATUS_TO_STATUS.get(self.data['carrier_status_detail'], self.data['carrier_status'])

		# Searching for the carrier_est_delivery. If it comes in local time or comes generalized
		if (date := getattr(obj_17track.time_metrics.estimated_delivery_date, 'from')) \
			or (date := getattr(obj_17track.time_metrics.estimated_delivery_date, 'to')):
			self.data['carrier_est_delivery'] = dt.fromisoformat(date).replace(tzinfo=None)

			if self.data['carrier_est_delivery'].time() == dt.min.time():  # If midnight, set to end of the day!
				self.data['carrier_est_delivery'] = self.data['carrier_est_delivery'].replace(hour=23, minute=59)

		# Build the latest event detail. If 'Delivered', get the real delivery date
		if last_event := obj_17track.latest_event:
			self.data['carrier_last_detail'] = (
				f"<b>{self.unscrub(last_event.stage or obj_17track.latest_status.status)}</b><br><br>"
				f"{last_event.description or 'Without Description'}<br><br>"
				f"{last_event.location or ((last_event.address.city or '') + (last_event.address.state or '') + (last_event.address.postal_code or ''))}"
			)

			# If parcel is Delivered we get the 'real_delivery_date' from the Latest Event Timestamp ISO
			if self.data['carrier_status'] == 'Delivered':
				self.data['carrier_real_delivery'] = dt.fromisoformat(last_event.time_iso).replace(tzinfo=None)

		return self.data


@frappe.whitelist(allow_guest=True, methods='POST')
def webhook_17track(**kwargs):
	""" POST To: {URL}/api/method/cargo_management.parcel_management.doctype.parcel.api.api_17track.webhook_17track """
	kwargs.pop('cmd')  # Remove extra data added by Frappe
	frappe.session.user = '17Track API'  # Quick Hack. Very useful

	try:
		# TODO: SIGN

		if kwargs['event'] != 'TRACKING_UPDATED':
			return 'Not a Tracker Update Webhook Event'  # TODO: Make something with this?

		#from cargo_management.parcel_management.doctype.parcel.parcel import Parcel
		#parcel = Parcel({'tracking_number': kwargs['data']['number']})  # This Wont Work for now!
		parcel = frappe.get_doc('Parcel', {'tracking_number': kwargs['data']['number']})  # Search Parcel
	except (KeyError, frappe.DoesNotExistError, Exception) as e:
		frappe.log_error(
			f"17Track Webhook: {type(e).__name__} -> {e}",
			reference_doctype='Parcel', reference_name=kwargs.get('data', {}).get('number', None)
		)

		return handle_exception(e)  # Handle as same as in frappe/app.py | handles -> http_status_code
	else:
		data = API17Track(carrier=parcel.carrier).convert_from_webhook(kwargs['data']['track_info'])  # This creates obj

		parcel.update_from_api_data(api_data=data)

		# Set because doc will be saved from webhook data. No validations needed.
		parcel.flags.ignore_validate = parcel.flags.ignore_mandatory = parcel.flags.ignore_links = True
		parcel.save(ignore_permissions=True)

		return f"Parcel {parcel.tracking_number} updated."
