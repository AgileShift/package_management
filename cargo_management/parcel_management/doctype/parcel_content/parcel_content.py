from frappe.model.document import Document


class ParcelContent(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amount: DF.Currency
		description: DF.TextEditor
		import_rate: DF.Float
		item_code: DF.Link | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		qty: DF.Int
		rate: DF.Currency
		tracking_number: DF.Data | None
	# end: auto-generated types
	pass
