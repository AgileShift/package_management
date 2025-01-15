import frappe
from cargo_management.utils import get_list_from_child_table
from frappe.model.document import Document


class WarehouseReceipt(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from cargo_management.warehouse_management.doctype.warehouse_receipt_line.warehouse_receipt_line import WarehouseReceiptLine
		from frappe.types import DF

		carrier_est_gross_weight: DF.Float
		departure_date: DF.Date | None
		status: DF.Literal["Open", "Awaiting Departure", "In Transit", "Sorting", "Finished"]
		transportation: DF.Literal["", "Sea", "Air"]
		volumetric_weight: DF.Float
		warehouse_est_gross_weight: DF.Float
		warehouse_receipt_lines: DF.Table[WarehouseReceiptLine]
	# end: auto-generated types

	def on_update(self):
		""" Add Warehouse Receipt Link to the Package. This allows to have mutual reference WR to Package. """
		# FIXME: If Warehouse Receipt is deleted, remove link from Package
		# TODO: Add extra fields from Warehouse Receipt -> Receipt Date & Weight

		# We only change the warehouse_receipt field if it is different from current.
		packages = get_list_from_child_table(self.warehouse_receipt_lines, 'parcel')

		if not packages:
			return

		# TODO: Improve
		frappe.db.sql("""
		UPDATE tabParcel
		SET warehouse_receipt = %(wr_name)s
		WHERE name IN %(packages)s AND COALESCE(warehouse_receipt, '') != %(wr_name)s
		""", {
			'wr_name': self.name,
			'packages': packages
		})

	# TODO: Actually change the status after the package is validated and creadted. maybe at status change from draft to open?

	def change_status(self, new_status):
		""" Validates the current status of the warehouse receipt and change it if it's possible. """

		# TODO: Validate this when status is changed on Form-View or List-View

		# TODO: FINISH
		if self.status != new_status and \
			(self.status == 'Open' and new_status == 'Awaiting Departure') or \
			(self.status in ['Open', 'Awaiting Departure'] and new_status == 'In Transit') or \
			(self.status in ['Open', 'Awaiting Departure', 'In Transit'] and new_status == 'Sorting') or \
			(self.status in ['Open', 'Awaiting Departure', 'In Transit', 'Sorting'] and new_status == 'Finished'):
			self.status = new_status
			return True

		return False
