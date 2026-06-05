/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.SaaSCheckout = publicWidget.Widget.extend({
    selector: '#subscribe_form',
    events: {
        'input #company_name': '_onCompanyNameInput',
        'input #customer_email': '_onEmailInput',
        'change #epg-privacy-check': '_onPrivacyChange',
    },

    init: function () {
        this._super.apply(this, arguments);
        this.checkTimeout = null;
        this.emailCheckTimeout = null;
        this.isSubdomainValid = false;
        this.isEmailValid = true; // True by default if email field doesn't exist
        this.isPrivacyValid = false;
        this.isCaptchaValid = false;
        console.log('[SaaS Checkout] Widget initialized');
    },

    start: function () {
        console.log('[SaaS Checkout] Widget started');
        this.$companyName = this.$('#company_name');
        this.$customerEmail = this.$('#customer_email');
        this.$subdomainCheck = this.$('#subdomain_check');
        this.$emailCheck = this.$('#email_check');
        this.$continueBtn = this.$('#continue_btn');
        this.$trialBtn = this.$('#trial_btn');
        
        if (this.$customerEmail.length) {
            this.isEmailValid = false; // Must validate if it exists
        }

        console.log('[SaaS Checkout] Elements found:', {
            companyName: this.$companyName.length,
            subdomainCheck: this.$subdomainCheck.length,
            continueBtn: this.$continueBtn.length,
            trialBtn: this.$trialBtn.length
        });
        
        if (this.$customerEmail.length && this.$customerEmail.val()) {
            this.$customerEmail.trigger('input');
        }
        if (this.$companyName.length && this.$companyName.val()) {
            this.$companyName.trigger('input');
        }

        this._loadRecaptcha();

        return this._super.apply(this, arguments);
    },

    _onPrivacyChange: function (ev) {
        this.isPrivacyValid = $(ev.currentTarget).is(':checked');
        this._updateButtons();
    },

    _loadRecaptcha: function () {
        if (typeof grecaptcha === 'undefined') {
            var script = document.createElement('script');
            script.src = 'https://www.google.com/recaptcha/api.js?onload=onloadSaasCaptcha&render=explicit';
            script.async = true;
            script.defer = true;
            document.head.appendChild(script);

            window.onloadSaasCaptcha = () => this._renderRecaptcha();
        } else {
            this._renderRecaptcha();
        }
    },

    _renderRecaptcha: function () {
        var el = this.$('#epg-recaptcha-element')[0];
        if (el && !el.hasChildNodes()) {
            grecaptcha.render(el, {
                'sitekey' : '6LccAj4sAAAAADJ4G-nOiqlwFTGQZoTYxY7LWwKR',
                'callback' : (token) => {
                    this.isCaptchaValid = true;
                    this._updateButtons();
                    // Remove Google's hidden field to avoid sending it in normal POST (Odoo controllers don't expect it)
                    const googleField = document.querySelector('textarea[name="g-recaptcha-response"]');
                    if (googleField) {
                        googleField.removeAttribute('name');
                    }
                },
                'expired-callback' : () => {
                    this.isCaptchaValid = false;
                    this._updateButtons();
                }
            });
        }
    },

    _onCompanyNameInput: function (ev) {
        console.log('[SaaS Checkout] Input detected:', $(ev.currentTarget).val());
        clearTimeout(this.checkTimeout);
        var companyName = $(ev.currentTarget).val().trim();

        if (companyName.length < 3) {
            this.$subdomainCheck.html('<span style="color: #94a3b8;">Enter at least 3 characters</span>');
            this.isSubdomainValid = false;
            this._updateButtons();
            return;
        }

        this.$subdomainCheck.html('<span style="color: #94a3b8;">Checking...</span>');
        this.isSubdomainValid = false;
        this._updateButtons();

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
                    this.$subdomainCheck.html('<span style="color: #10b981;">✓ Available! Your subdomain will be: ' + result.subdomain + '.eficienciayproductividadglobal.com</span>');
                    this.isSubdomainValid = true;
                } else {
                    const msg = result ? result.message : 'Unknown error';
                    this.$subdomainCheck.html('<span style="color: #ef4444;">✗ ' + msg + '</span>');
                    this.isSubdomainValid = false;
                }
                this._updateButtons();
            })
            .catch((error) => {
                console.error('[SaaS Checkout] Error checking company name', error);
                this.$subdomainCheck.html('<span style="color: #f59e0b;">Unable to verify availability</span>');
                // Allow them to try submission anyway in case of transient error
                this.isSubdomainValid = true;
                this._updateButtons();
            });
    },

    _onEmailInput: function (ev) {
        clearTimeout(this.emailCheckTimeout);
        var email = $(ev.currentTarget).val().trim();
        
        // Basic email regex
        var emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

        if (!emailRegex.test(email)) {
            this.$emailCheck.html('<span style="color: #94a3b8;">Please enter a valid email address</span>');
            this.isEmailValid = false;
            this._updateButtons();
            return;
        }

        this.$emailCheck.html('<span style="color: #94a3b8;">Checking...</span>');
        this.isEmailValid = false;
        this._updateButtons();

        this.emailCheckTimeout = setTimeout(() => {
            this._checkEmailAvailability(email);
        }, 500);
    },

    _checkEmailAvailability: function (email) {
        fetch('/saas/check_email_availability', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                jsonrpc: '2.0',
                method: 'call',
                params: {
                    email: email
                }
            })
        })
            .then(response => response.json())
            .then(data => {
                const result = data.result;

                if (result && result.available) {
                    this.$emailCheck.html('<span style="color: #10b981;">✓ Email available</span>');
                    this.isEmailValid = true;
                } else {
                    const msg = result ? result.message : 'Email already in use';
                    this.$emailCheck.html('<span style="color: #ef4444;">✗ ' + msg + ' <a href="/web/login" style="color: #60a5fa; text-decoration: underline;">Log in instead</a></span>');
                    this.isEmailValid = false;
                }
                this._updateButtons();
            })
            .catch((error) => {
                console.error('[SaaS Checkout] Error checking email', error);
                this.$emailCheck.html('<span style="color: #f59e0b;">Unable to verify email</span>');
                this.isEmailValid = true;
                this._updateButtons();
            });
    },

    _updateButtons: function () {
        const canSubmit = this.isSubdomainValid && this.isEmailValid && this.isPrivacyValid && this.isCaptchaValid;
        this.$continueBtn.prop('disabled', !canSubmit);
        this.$trialBtn.prop('disabled', !canSubmit);
        
        if (!canSubmit) {
            let reasons = [];
            if (!this.isSubdomainValid) reasons.push("subdominio válido");
            if (!this.isEmailValid) reasons.push("email válido");
            if (!this.isPrivacyValid) reasons.push("aceptar privacidad");
            if (!this.isCaptchaValid) reasons.push("completar captcha");
            
            const title = "Requerido: " + reasons.join(", ");
            this.$continueBtn.attr('title', title);
            this.$trialBtn.attr('title', title);
        } else {
            this.$continueBtn.removeAttr('title');
            this.$trialBtn.removeAttr('title');
        }
    },
});

export default publicWidget.registry.SaaSCheckout;
