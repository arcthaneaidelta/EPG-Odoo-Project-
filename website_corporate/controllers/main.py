from odoo import http
from odoo.http import request


class WebsiteCorporate(http.Controller):

    @http.route("/thank-you", type="http", auth="public", website=True)
    def thank_you(self):
        return request.render("website_corporate.thank_you")
