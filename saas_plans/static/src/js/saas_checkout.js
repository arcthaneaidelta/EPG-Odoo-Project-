/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.SaaSCheckout = publicWidget.Widget.extend({
    selector: '#subscribe_form',
    events: {
        'input #company_name': '_onCompanyNameInput',
    },

    init: function () {
        this._super.apply(this, arguments);
        this.checkTimeout = null;
        console.log('[SaaS Checkout] Widget initialized');
    },

    start: function () {
        console.log('[SaaS Checkout] Widget started');
        this.$companyName = this.$('#company_name');
        this.$subdomainCheck = this.$('#subdomain_check');
        this.$continueBtn = this.$('#continue_btn');

        console.log('[SaaS Checkout] Elements found:', {
            companyName: this.$companyName.length,
            subdomainCheck: this.$subdomainCheck.length,
            continueBtn: this.$continueBtn.length
        });

        return this._super.apply(this, arguments);
    },

    _onCompanyNameInput: function (ev) {
        console.log('[SaaS Checkout] Input detected:', $(ev.currentTarget).val());
        clearTimeout(this.checkTimeout);
        var companyName = $(ev.currentTarget).val().trim();

        if (companyName.length < 3) {
            this.$subdomainCheck.html('<span style="color: #94a3b8;">Enter at least 3 characters</span>');
            this.$continueBtn.prop('disabled', true);
            return;
        }

        this.$subdomainCheck.html('<span style="color: #94a3b8;">Checking...</span>');
        this.$continueBtn.prop('disabled', true);

        this.checkTimeout = setTimeout(() => {
            this._checkAvailability(companyName);
        }, 500);
    },

    _checkAvailability: function (companyName) {
        console.log('[SaaS Checkout] Checking availability for:', companyName);

        // Use native fetch to avoid dependency issues with System's RPC modules in frontend
        fetch('/saas/check_company_name', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                jsonrpc: '2.0',
                method: 'call',
                params: {
                    company_name: companyName
                }
            })
        })
            .then(response => response.json())
            .then(data => {
                console.log('[SaaS Checkout] Result:', data);
                const result = data.result;

                if (result && result.available) {
                    this.$subdomainCheck.html('<span style="color: #10b981;">✓ Available! Your subdomain will be: ' + result.subdomain + '.abc.com</span>');
                    this.$continueBtn.prop('disabled', false);
                } else {
                    const msg = result ? result.message : 'Unknown error';
                    this.$subdomainCheck.html('<span style="color: #ef4444;">✗ ' + msg + '</span>');
                    this.$continueBtn.prop('disabled', true);
                }
            })
            .catch((error) => {
                console.error('[SaaS Checkout] Error checking company name', error);
                this.$subdomainCheck.html('<span style="color: #f59e0b;">Unable to verify availability</span>');
                // Allow them to try submission anyway in case of transient error
                this.$continueBtn.prop('disabled', false);
            });
    },
});

export default publicWidget.registry.SaaSCheckout;
