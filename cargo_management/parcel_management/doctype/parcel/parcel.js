frappe.ui.form.on('Parcel', {

	setup(frm) {},

	onload(frm) {
		// Moving this piece of code outside setup. because it's not working inside "setup"
		frm.page.sidebar.toggle(false);
		// FIXME: Observe if the indicator changes. This is useful for the 'Not Saved' status aka is_dirty(). We cannot read that from the events available
		const observer = new MutationObserver(() => {
			frm.layout.show_message('');      // Clear Message because it's possible that data changes!
			frm.page.clear_custom_actions();  // Clear Custom buttons
			frm.page.indicator.next().remove(); // Remove the extra indicator if the indicator changes
		});
		observer.observe(frm.page.indicator.get(0), {childList: true}); // Observe the 'indicator' for changes

		// Setting custom queries
		frm.set_query('item_code', 'content', () => {
			return {
				filters: {
					'is_sales_item': true,
					'has_variants': false
				}
			}
		});

		// Setting Currency Labels
		frm.set_currency_labels(['total', 'shipping_amount'], 'USD');
		frm.set_currency_labels(['rate', 'amount'], 'USD', 'content');
	},

	refresh(frm) {
		if (frm.is_new()) {
			return;
		}

		frm.page.indicator.parent().append(cargo_management.transportation_indicator(frm.doc.transportation)); // Add Extra Indicator

		frm.events.show_explained_status(frm); // Show 'Explained Status' as Intro Message
		frm.events.build_custom_actions(frm);  // Adding custom buttons

		//frm.trigger('parcel_preview_dialog');
	},

	tracking_number(frm) {
		frm.doc.tracking_number = frm.doc.tracking_number.trim().toUpperCase();  // Sanitize field

		if (!frm.doc.tracking_number) {
			return;
		}

		frm.doc.carrier = cargo_management.find_carrier_by_tracking_number(frm.doc.tracking_number).carrier;

		refresh_many(['tracking_number', 'carrier']);
	},

	shipping_amount(frm) {
		frm.events.calculate_total(frm);
	},

	// Custom Functions

	show_explained_status(frm) {
		frm.doc.explained_status.message.forEach(m => frm.layout.show_message(m, ''));  // FIXME: Core overrides color
		frm.layout.message.removeClass().addClass('form-message ' + frm.doc.explained_status.color);
	},

	build_custom_actions(frm) {
		const carriers_settings = cargo_management.load_carrier_settings(frm.doc.carrier);

		if (carriers_settings.api) {
			frm.add_custom_button(__('Get Updates from Carrier'), () => frm.events.get_data_from_api(frm));
		}

		if (frm.doc.assisted_purchase) { // If is Assisted Purchase will have related Sales Order and Sales Order Item
			frm.add_custom_button(__('Sales Order'), () => frm.events.sales_order_dialog(frm), __('Get Items From'));
		}

		frm.add_custom_button(__('Previsualization'), () => frm.events.parcel_preview_dialog(frm));


		frm.add_custom_button(__('Search'), () => cargo_management.open_carriers_dialog(frm.doc));
	},

	get_data_from_api(frm) {
		// TODO: WORK ON THIS. We have to delete some data
		frappe.call({
			method: 'cargo_management.parcel_management.doctype.parcel.actions.get_data_from_api',
			freeze: true, freeze_message: __('Updating from Carrier...'), args: {source_name: frm.doc.name},
			callback: (r) => {
				// FIXME: "Not Saved" indicator cannot be changed.
				console.log('Need to work in here. problems in v14');
				//frappe.model.sync(r.message);
				//frm.refresh();
			}
		});
	},

	parcel_preview_dialog(frm) {
		const preview_dialog = new frappe.ui.Dialog({
			title: 'General Overview', size: 'extra-large',
			fields: [
				{fieldtype: 'HTML', fieldname: 'preview'},
			]
		});

		preview_dialog.show()

		preview_dialog.fields_dict.preview.$wrapper.html(`
		<div class="container">
			<h3 class="text-center">${frm.doc.carrier} - ${frm.doc.tracking_number} ${cargo_management.transportation_indicator(frm.doc.transportation)}</h3>

			<div class="row">
				<div class="col-6">
					<div class="card">
						<div class="card-header">Información General</div>
						<ul class="list-group list-group-flush">
							<li class="list-group-item">Shipper: <strong>${frm.doc.shipper}</strong></li>
							<li class="list-group-item"># de Orden: <strong>${frm.doc.order_number}</strong></li>
							<li class="list-group-item">Fecha de Compra: <strong>${frm.doc.order_date}</strong></li>
						</ul>
					</div>
				</div>
				<div class="col-6">
					<div class="card">
						<div class="card-header">Descripcion</div>
						<ul class="list-group list-group-flush">
							${frm.doc.content.map((c) => {
								return (`<li class="list-group-item">Descripcion: <strong>${c.description}</strong> | Tracking: <strong>${c.tracking_number}</strong></li>`);
							}).join('') }
						</ul>
					</div>
				</div>
			</div>

			<div class="d-flex flex-row justify-content-between align-items-start border rounded p-3 my-3">
				<div>
					<div class="mb-2"><span class="badge badge-primary">Fecha de Orden</span> <strong>${frm.doc.order_date}</strong></div>
				</div>
				<div class="d-flex flex-column">
					<div class="mb-2"><span class="badge badge-secondary">Fecha Estimada de Llegada 1</span> <strong>${frm.doc.est_delivery_1}</strong></div>
					<div><span class="badge badge-secondary">Fecha Estimada de Llegada 2</span> <strong>${frm.doc.est_delivery_2}</strong></div>
				</div>
				<div>
					<div><span class="badge badge-success">Fecha Estimada de Despacho</span> <strong>${frm.doc.est_departure}</strong></div>
				</div>
				<div>
					<div><span class="badge badge-success">Fecha Estimada de Entrega</span> <strong>${frm.doc.est_departure}</strong></div>
				</div>
			</div>

		</div>`);
	},

	//https://github.com/frappe/frappe/pull/12471 and https://github.com/frappe/frappe/pull/14181/files
	sales_order_dialog(frm) {
		const so_dialog = new frappe.ui.form.MultiSelectDialog({
			doctype: 'Sales Order',
			target: frm,
			setters: {
				delivery_date: undefined,
				status: undefined
			},
			add_filters_group: 1,
			get_query: () => {
				return {
					filters: {  // TODO: Only uncompleted orders!
						docstatus: 1,
						customer: frm.doc.customer,
					}
				};
			},
			action: (selections) => {
				if (selections.length === 0) {
					frappe.msgprint(__("Please select {0}", [so_dialog.doctype]))
					return;
				}
				// so_dialog.dialog.hide();
				frm.events.so_items_dialog(frm, selections);
			}
		});
	},

	so_items_dialog: async function (frm, sales_orders) {
		// Getting all sales order items from Sales Order
		let sale_order_items = await frappe.db.get_list('Sales Order Item', {
			filters: {'parent': ['in', sales_orders]},
			fields: ['name as docname', 'item_code', 'description', 'qty', 'rate']
		});

		const so_items_dialog = new frappe.ui.form.MultiSelectDialog({
			doctype: 'Sales Order Item',
			target: frm,
			setters: {
				// item_code: undefined,
				// qty: undefined,
				// rate: undefined
			},
			data_fields: [
				{
					fieldtype: 'Currency',
					options: "USD",
					fieldname: "rate",
					read_only: 1,
					hidden: 1,
				},
				{
					fieldname: 'item_code',
					fieldtype: 'Data',
					label: __('Item Code')
				}],
			get_query: () => {
				return {
					filters: {
						parent: ['in', sales_orders]
					}
				}
			},
			add_filters_group: 1,
			action: (jkjk) => {
				console.log(jkjk);
			},
			primary_action_label: __('Select')
		});

	},

	calculate_total(frm) {
		frm.set_value('total', frm.get_sum('content', 'amount') + frm.doc.shipping_amount);
	},
	calculate_content_amounts_and_total(frm, cdt, cdn) {
		let row = locals[cdt][cdn]; // Getting Content Child Row being edited

		row.amount = row.qty * row.rate;
		refresh_field('amount', cdn, 'content');

		frm.events.calculate_total(frm); // Calculate the parent 'total' field
	}
});

frappe.ui.form.on('Parcel Content', {
	content_remove(frm) {
		frm.events.calculate_total(frm);
	},

	qty(frm, cdt, cdn) {
		frm.events.calculate_content_amounts_and_total(frm, cdt, cdn);
	},

	rate(frm, cdt, cdn) {
		frm.events.calculate_content_amounts_and_total(frm, cdt, cdn);
	},
});
//201 - FIXME: Giving PROBLEMS
// 254 -> Working on Frappe Boot Info for Carriers!
