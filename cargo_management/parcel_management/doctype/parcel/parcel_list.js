frappe.listview_settings['Parcel'] = {
	hide_name_filter: true,
	add_fields: ['carrier'],
	filters: [
		['status', 'not in', ['Finished', 'Cancelled', 'Never Arrived', 'Returned to Sender']] // aka 'Active Parcels'
	],

	onload(listview) {
		const {tracking_number: tracking_number_field, customer_name: customer_name_field} = listview.page.fields_dict;

		listview.page.sidebar.toggle(false);

		// Override: onchange() method set in frappe/list/base_list.js -> make_standard_filters()
		tracking_number_field.df.onchange = customer_name_field.df.onchange = function () {
			// Remove '%' added in frappe/list/base_list.js -> get_standard_filters() when the listview loads and update both UI and internal values
			this.value = this.input.value = this.get_input_value().replaceAll('%', '').trim().toUpperCase(); // this.set_input() is not working

			if (this.value !== this.last_value) {
				listview.filter_area.refresh_list_view(); // refresh_list_view() if value has changed. TODO: debounced_refresh_list_view?
			}
		};

		/* Override to add 'or_filters'. FIXME: Will be better to have it on backend to solve: gets_args + get_count_str + get_stats
		 * frappe hook: 'permission_query_conditions' Wont work, It get called after we have build the frappe
		 * check this: override_whitelisted_methods. The problem is this method is HEAVILY used
		 * TODO: listview.get_count_str() => This call frappe.db.count() using 'filters' not 'or_filters'
		 * TODO: listview.list_sidebar.get_stats() => This call frappe.desk.reportview.get_sidebar_stats using 'filters' not 'or_filters' */
		listview.get_args = function () {
			let args = frappe.views.ListView.prototype.get_args.call(listview);  // Calling his super for the args

			const tracking_number_filter = args.filters.findIndex(f => f[1] === 'tracking_number');  // f -> ['Doctype', 'field', 'sql_search_term', 'value']

			if (tracking_number_filter >= 0) {  // We have 'tracking_name' filter being filtered. -> tracking_number_filter will contain index if found
				args.filters.splice(tracking_number_filter, 1);  // Removing 'name' filter from 'filters'. It's a 'standard_filter'

				const search_term = cargo_management.find_carrier_by_tracking_number(tracking_number_field.get_input_value()).search_term;

				// TODO: WORK -> We will not use the main field from now on
				args.or_filters = ['name', 'tracking_number'].map(field => [
					args.doctype, field, 'like', '%' + search_term + '%'
				]); // Mapping each field to 'or_filters' for the necessary fields to search
				args.or_filters.push(['Parcel Content', 'tracking_number', 'like', '%' + search_term + '%'])  // This acts as a consolidated tracking number
			}

			return args;
		};

		//FIXME: Delete after Finish! frappe.ui.form.make_quick_entry('Parcel', null, null, '');
	},

	// Unused: light-blue. // TODO: Migrate to Document States? Maybe when frappe core starts using it.
	get_indicator: (doc) => [__(doc.status), {
		'Awaiting Receipt': 'blue',
		'Awaiting Confirmation': 'orange',
		'In Extraordinary Confirmation': 'pink',
		'Awaiting Departure': 'yellow',
		'In Transit': 'purple',
		'In Customs': 'gray',
		'Sorting': 'green',
		'To Bill': 'green',
		'Unpaid': 'red',
		'For Delivery or Pickup': 'cyan',
		'Finished': 'darkgrey',
		'Cancelled': 'red',
		'Never Arrived': 'red',
		'Returned to Sender': 'red',
	}[doc.status], 'status,=,' + doc.status],

	button: {
		show: () => true,
		get_label: () => __('Search'),
		get_description: () => '',
		action: (doc) => cargo_management.open_carriers_dialog(doc)
	},

	formatters: {
		transportation: (value) => cargo_management.transportation_formatter(value),
		sub_status: (value) => value, // TODO: Complete this
		name: (value, df, doc) => (value !== doc.tracking_number) ? `<b>${value}</b>` : ''
	}

};
// 119 FIXME: Create more functions, and move them to cargo_management.js
// 6 warning, 4 typo // TODO: 115 -> Working on frappe boot info
// 83 TODO: listview.get_args WE NEED TO MOVE THIS. To Work on the backend
