frappe.ui.form.on('Warehouse Receipt', {
	// TODO: Delete Most of this

	setup: function (frm) {
		frm.page.sidebar.toggle(false); // Hide Sidebar
	},

	tracking_number: function (frm) {
		frm.doc.tracking_number = frm.doc.tracking_number.trim().toUpperCase();  // Sanitize field

		if (!frm.doc.tracking_number) {
			return;
		}

		frappe.call({
			method: 'cargo_management.warehouse_customization.doctype.warehouse_receipt.actions.find_package_by_tracking_number',
			type: 'GET',
			freeze: true,
			freeze_message: __('Searching Package...'),
			args: {tracking_number: frm.doc.tracking_number},
			callback: (r) => { // TODO: Maybe a Switch
				if (r.message.coincidences) {
					frm.events.show_selector_dialog(frm, r.message);
				} else if (r.message.coincidence) {
					frappe.show_alert('Paquete Pre-Alertado.');
					frm.events.set_package(frm, r.message.coincidence);
				} else {
					frappe.show_alert('Paquete sin Pre-Alerta.');
				}
			}
		});
	},

	// Custom Functions
	show_selector_dialog: function (frm, opts) {
		// https://frappeframework.com/docs/v13/user/en/api/controls & https://frappeframework.com/docs/v13/user/en/api/dialog
		// MultiselectDialog with Package List -> Issue: can select multiple
		// Dialog with a Table Field of Package List -> Issue: can select multiple and needs a select button
		// MultiCheck Field with Package List as Options -> Issue: can select multiple. No extra data for package identification
		// Select Field with Package List as Options -> Issue: Small extra data for package identification, and need a select button or event trigger.
		// LinkSelector with Package List as Options -> Issue: its exactly what we need. But without search and button and configurable extra fields

		const selector_dialog = new frappe.ui.Dialog({
			title: __('Coincidences found for: {0}', [frm.doc.tracking_number]),
			static: false,          // Cannot cancel touching outside pop-up
			no_cancel_flag: false,  // Cannot cancel with keyboard
			size: 'extra-large',
			fields: [{fieldtype: 'HTML', fieldname: 'table_html'}]
		});

		selector_dialog.fields_dict.table_html.$wrapper
			.html(frappe.render_template('package_selector', {
				search_term: opts.search_term,
				coincidences: opts.coincidences
			}))
			.find('a').on('click', e => {
			e.preventDefault();
			selector_dialog.hide();
			frm.events.set_package(frm, $(e.target).attr('data-value'));
		});

		selector_dialog.show();
	},

	set_package: function (frm, coincidence) {
		const doc_name = coincidence.name || coincidence;

		frappe.db.get_doc('Package', doc_name).then(doc => {
			frm.doc.tracking_number = doc.name;
			frm.doc.carrier = doc.carrier;

			frm.transportation.$checkbox_area.find(`:checkbox[data-unit="${doc.transportation}"]`).trigger('click'); // This Trigger on_change

			// FIXME: Join this fields?
			frm.doc.shipper = doc.shipper;
			frm.doc.consignee = doc.customer_name;

			frm.doc.customer_description = (doc.content.length > 0) ? doc.content.map(c => 'Item: ' + c.description + '\nCantidad: ' + c.qty).join("\n\n") : null;

			frm.refresh_fields();
			frm.events.show_alerts(frm); // FIXME: Work on this
		});
	},

	show_alerts(frm) {
		// TODO: Make this come from API?
		frm.dashboard.clear_headline();

		if (frm.doc.customer_description) {
			frm.layout.show_message('<b>No es necesario abrir el paquete. <br> Cliente Pre-Alerto el contenido.</b>', '');
			frm.layout.message.removeClass().addClass('form-message ' + 'green');  // FIXME: Core overrides color
		}
	},
});

frappe.ui.form.on('Warehouse Receipt Line', {});
// FIXME 134
