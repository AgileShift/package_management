frappe.ui.form.on('Cargo Shipment Receipt', {

    onload: function (frm) {
        // Adding the two possible ways to trigger a fetch for customer_name
        frm.add_fetch('package', 'customer_name', 'customer_name');
        frm.add_fetch('customer', 'customer_name', 'customer_name');

	    frm.set_query('package', 'cargo_shipment_receipt_lines', () => {
            return {
                filters: {
                    status: ['not in', ['Available to Pickup', 'Finished']]
                }
            };
        });
    },

    cargo_shipment: function (frm) {
        if (!frm.doc.cargo_shipment) {
            return;
        }

        frm.clear_table('cargo_shipment_receipt_warehouse_lines');
        frm.clear_table('cargo_shipment_receipt_lines');

        frappe.call({
            method: 'cargo_management.shipment_customization.doctype.cargo_shipment_receipt.actions.get_packages_and_wr_in_cargo_shipment',
            args: {cargo_shipment: frm.doc.cargo_shipment},
            freeze: true,
            freeze_message: __('Adding Packages...')
        }).then(r => {

            r.message.packages.forEach(package_doc => {
                frm.add_child('cargo_shipment_receipt_lines', {
                    'package': package_doc.name,
                    // 'item_code': package_doc.item_code,  TODO: This is not working, because the package is set one time
                    'customer': package_doc.customer,
                    'customer_name': package_doc.customer_name,
                    'carrier_weight': package_doc.carrier_est_weight,
                    'content': package_doc.content
                });
            });

            r.message.warehouse_receipts.forEach(wr => {
                frm.add_child('cargo_shipment_receipt_warehouse_lines', {
                    'warehouse_receipt': wr
                })
            })

            frm.refresh_field('cargo_shipment_receipt_warehouse_lines'); // Refresh the child table.
            frm.refresh_field('cargo_shipment_receipt_lines'); // Refresh the child table.
        });

    }
});

// Child Table
frappe.ui.form.on('Cargo Shipment Receipt Line', {
    // TODO: We should allow always customer to be read not read_only?
});