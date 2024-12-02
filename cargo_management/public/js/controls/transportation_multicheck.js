frappe.ui.form.ControlTransportationMultiCheck = class ControlTransportationMultiCheck extends frappe.ui.form.ControlMultiCheckSingle { // FIXME ControlMultiCheckSingle
	// Extends from ControlMultiCheckSingle to create a 'TransportationMultiCheck'
	// TODO: Create a Control from scratch to use Radio Buttons instead of Checkboxes

	// See: https://frappeframework.com/docs/user/en/guides/app-development/how-to-improve-a-standard-control
	parse_df_options() {
		// No need to call -> super(). See: /form/controls/multicheck.js -> parse_df_options(); From the parent class

		// 'checked': Gives Error if a value not the default is selected in quickEntry. It shows selected the default always
		this.options = this.df.options.split('\n').map(t => ({
			value: t, description: __(t), //checked: t === this.df.default,
			label: __(t).toUpperCase() + cargo_management.icon_html(cargo_management.TRANSPORTATIONS[t].icon),
			color: cargo_management.TRANSPORTATIONS[t].color
		}));

		console.log(this.options)
	}

	get_checkbox_element(option) {
		let ele = super.get_checkbox_element(option);

		ele.css('border', `1px solid ${option.color}`);
		ele.find('label').css('color', option.color);

		return ele;
	}

	// Refer to: /form/controls/check.js -> set_input();
	set_input(value) {
		this.last_value = this.value;
		this.value = value;

		console.log(value)

		this.set_checked_options();  // Set Initial Value. Refer to: /form/controls/multicheck.js -> set_checked_options();
	}
}
