frappe.ui.form.on('Cargo Shipment Receipt', {
	// TODO: On Save set customer on the package that are not set!
	// TODO: Formatter for Package item?

	setup(frm) {
		frm.page.sidebar.toggle(false); // Hide Sidebar to focus better on the doc
	},

	onload: function (frm) {
		// Adding the two possible ways to trigger a fetch for customer_name : FIXME REVIEW THIS!. what happens on multiple customers same tracking?
		frm.add_fetch('package', 'customer_name', 'customer_name');
		frm.add_fetch('customer', 'customer_name', 'customer_name');

		// TODO: Set Query for cargo_shipment_receipt_warehouse_lines
		frm.set_query('package', 'cargo_shipment_receipt_lines', () => {
			return {
				filters: {
					status: ['not in', ['In Customs', 'Sorting', 'Available to Pickup', 'Finished']],
				}
			};
		});
		frm.set_query('item_code', 'cargo_shipment_receipt_lines', () => {
			return {
				filters: {
					name: ['not like', '%ASIS%']
				}
			}
		})
	},

	refresh: function (frm) {
		// TODO: after UI release: Child table dont update after save(validate method sorts the child table)
		// TODO: Add a button to sort child table by customer name.
		// TODO: Add intro message when the cargo shipment is on a cargo shipment receipt
		// TODO: Add Progress: dashboard.add_progress or frappe.chart of type: percentage

		if (frm.is_new()) {
			return;
		}

		if (frm.doc.status === 'Awaiting Receipt' || frm.doc.status === 'Sorting') { // Awaiting or actually sorting

			frm.page.add_action_item(__('Mark as Sorting'), () => {
				frappe.call({
					method: 'cargo_management.shipment_management.doctype.cargo_shipment_receipt.actions.update_status',
					freeze: true,
					args: {
						source_doc_name: frm.doc.name,
						new_status: 'Sorting'
					}
				});
			});

			if (frm.doc.status === 'Sorting') {
				frm.add_custom_button(__('Sales Invoice'), () => {
					frappe.call({
						method: 'cargo_management.shipment_management.doctype.cargo_shipment_receipt.actions.make_sales_invoice',
						args: {doc: frm.doc},
						freeze: true,
						freeze_message: __('Creating Sales Invoice...')
					});//.then(r => { // Return customers invoices
					// frm.refresh_field('cargo_shipment_receipt_lines');
					// });
				}, __('Create'));

				frm.page.set_inner_btn_group_as_primary(__('Create'));
			}
		}
	},

	cargo_shipment: function (frm) {
		if (!frm.doc.cargo_shipment) {
			return;
		}

		// We clear the table each time to avoid duplication
		frm.clear_table('cargo_shipment_receipt_lines');

		frappe.call({
			method: 'cargo_management.shipment_management.utils.get_packages_and_wr_in_cargo_shipment',
			type: 'GET',
			args: {cargo_shipment: frm.doc.cargo_shipment},
			freeze: true,
			freeze_message: __('Adding Packages...'),
		}).then(r => {

			r.message.packages.forEach(package_doc => {
				frm.add_child('cargo_shipment_receipt_lines', {
					'content': package_doc.customer_description,
					// 'item_code': package_doc.item_code, TODO: This is not working, because the package can have more than once item code

					'customer': package_doc.customer,
					'customer_name': package_doc.customer_name,

					'package': package_doc.name,
					'package_2': package_doc.tracking_number,
					'carrier_est_weight': package_doc.carrier_est_weight,

					'assisted_purchase': package_doc.assisted_purchase,
					'transportation': package_doc.transportation,
					'shipper': package_doc.shipper,
				});
			});

			// Refresh the modified tables inside the callback after execution is done
			frm.refresh_field('cargo_shipment_receipt_lines');
		});

	},

	// TODO: This can be improved more dynamically -> // HELPERS -> Fix or Make more Dynamic
	update_item_code: function (frm, cdt, cdn, item_code) {
		locals[cdt][cdn].item_code = item_code;  // Getting Content Child Row being edited
		refresh_field('item_code', cdn, 'cargo_shipment_receipt_lines');
		frm.dirty();
	},
});



// Child Table
frappe.ui.form.on('Cargo Shipment Receipt Line', {
	// TODO: We should allow always customer to be read not read_only?

	// TODO: Add a button to trigger this info!
	// TODO ADD Extra Info: Warehouse Weight, Carrier Weight, Gross Weight:
	gross_weight: function (frm) {
		frm.set_value('gross_weight', frm.get_sum('cargo_shipment_receipt_lines', 'gross_weight'));
	},

	// TODO: This can be improved more dynamically -> // HELPERS -> Fix or Make more Dynamic
	default_weight: function (frm, cdt, cdn) {
		locals[cdt][cdn].gross_weight = 1.00;  // Getting Content Child Row being edited
		refresh_field('gross_weight', cdn, 'cargo_shipment_receipt_lines');
		frm.dirty();
	},

	most_used_item_code_1: (frm, cdt, cdn) => frm.events.update_item_code(frm, cdt, cdn, 'IP Varios - PESO'),
	most_used_item_code_2: (frm, cdt, cdn) => frm.events.update_item_code(frm, cdt, cdn, 'IP Ropa - PESO'),
	most_used_item_code_3: (frm, cdt, cdn) => frm.events.update_item_code(frm, cdt, cdn, 'IP Zapatos - PESO'),
	most_used_item_code_4: (frm, cdt, cdn) => frm.events.update_item_code(frm, cdt, cdn, 'IP Cosméticos - PESO'),
	most_used_item_code_5: (frm, cdt, cdn) => frm.events.update_item_code(frm, cdt, cdn, 'IP Skincare - PESO'),
	most_used_item_code_6: (frm, cdt, cdn) => frm.events.update_item_code(frm, cdt, cdn, 'IP Perfumes - PESO'),
	most_used_item_code_7: (frm, cdt, cdn) => frm.events.update_item_code(frm, cdt, cdn, 'IP Peluches - PESO'),
	most_used_item_code_8: (frm, cdt, cdn) => frm.events.update_item_code(frm, cdt, cdn, 'IP Juguetes - PESO'),
	most_used_item_code_9: (frm, cdt, cdn) => frm.events.update_item_code(frm, cdt, cdn, 'IP Reloj - PESO'),
	most_used_item_code_10: (frm, cdt, cdn) => frm.events.update_item_code(frm, cdt, cdn, 'IP Electronico - PESO'),
	most_used_item_code_11: (frm, cdt, cdn) => frm.events.update_item_code(frm, cdt, cdn, 'IP Salud y Hogar - PESO'),
	most_used_item_code_12: (frm, cdt, cdn) => frm.events.update_item_code(frm, cdt, cdn, 'IP Vitaminas y Suplementos - PESO'),
	most_used_item_code_13: (frm, cdt, cdn) => frm.events.update_item_code(frm, cdt, cdn, 'IP Repuestos - PESO'),
	most_used_item_code_14: (frm, cdt, cdn) => frm.events.update_item_code(frm, cdt, cdn, 'IP Repuesto Auto - PESO'),
	most_used_item_code_15: (frm, cdt, cdn) => frm.events.update_item_code(frm, cdt, cdn, 'IP Repuesto de Moto - PESO')

});
