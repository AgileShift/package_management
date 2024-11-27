import frappe
from cargo_management.parcel_management.doctype.parcel.actions import find_carrier_by_tracking_number


@frappe.whitelist(methods='GET')
def find_package_by_tracking_number(tracking_number: str):
	""" Tries to Find a Package Doc giving only a tracking number """
	result = find_carrier_by_tracking_number(tracking_number)  # Returns tracking_number sanitized

	# TODO: Delete consolidated_tracking_numbers
	# ToDo: OPTIMIZE the build of query params: 1ZY853E7YW41358480
	coincidences = frappe.get_list(
		'Parcel',
		fields=['name', 'tracking_number', 'consolidated_tracking_numbers', 'customer_name', 'transportation'],
		or_filters={
			'name': ['LIKE', '%{}%'.format(result['search_term'])],
			'tracking_number': ['LIKE', '%{}%'.format(result['search_term'])],
			'consolidated_tracking_numbers': ['LIKE', '%{}%'.format(result['search_term'])]
		}
	)

	# TODO: what if only 1 coincidence and its a partial match. Its likely to be a exact match
	# TODO: What if multiple coincidences are find and 1 of them its a exact match?
	# TODO: if search request its inside consolidated
	if not coincidences:
		return {}  # No Package with similar name or tracking_number
	elif len(coincidences) == 1 and tracking_number in (coincidences[0].name, coincidences[0].tracking_number):
		return {'coincidence': coincidences[0]}  # Only one coincidence and its equal. Exact match

	return {  # TODO: Return always coincidences, even if its only one? and possible a unique one
		'coincidences': coincidences,
		'search_term': result['search_term']
	}
