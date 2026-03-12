# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request

class SaasClientController(http.Controller):

    @http.route('/suspended', type='http', auth='public', website=False)
    def render_suspended_page(self, **kw):
        """Render a custom HTML page when the subscription is suspended."""
        manager_url = request.env['ir.config_parameter'].sudo().get_param('saas.manager_url', '')
        
        # HTML Template for the suspended page
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Database Suspended</title>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
            <style>
                :root {{
                    --primary: #5A67D8; /* Modern Indigo */
                    --primary-hover: #434190;
                    --bg-color: #F7FAFC;
                    --card-bg: #FFFFFF;
                    --text-main: #2D3748;
                    --text-muted: #718096;
                    --danger: #E53E3E;
                }}
                body {{
                    margin: 0;
                    padding: 0;
                    font-family: 'Inter', sans-serif;
                    background-color: var(--bg-color);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    min-height: 100vh;
                    color: var(--text-main);
                }}
                .container {{
                    background-color: var(--card-bg);
                    padding: 3rem 4rem;
                    border-radius: 16px;
                    box-shadow: 0 10px 25px rgba(0,0,0,0.05);
                    max-width: 500px;
                    text-align: center;
                    animation: fadeIn 0.5s ease-out;
                }}
                .icon-box {{
                    width: 80px;
                    height: 80px;
                    background-color: #FFF5F5;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin: 0 auto 1.5rem auto;
                }}
                .icon-box svg {{
                    width: 40px;
                    height: 40px;
                    color: var(--danger);
                }}
                h1 {{
                    font-weight: 800;
                    font-size: 1.8rem;
                    margin: 0 0 1rem 0;
                }}
                p {{
                    font-size: 1rem;
                    line-height: 1.6;
                    color: var(--text-muted);
                    margin: 0 0 2rem 0;
                }}
                .btn {{
                    display: inline-block;
                    background-color: var(--primary);
                    color: white;
                    text-decoration: none;
                    font-weight: 600;
                    padding: 0.8rem 2rem;
                    border-radius: 8px;
                    transition: all 0.2s ease;
                    box-shadow: 0 4px 6px rgba(90, 103, 216, 0.25);
                }}
                .btn:hover {{
                    background-color: var(--primary-hover);
                    transform: translateY(-2px);
                    box-shadow: 0 6px 12px rgba(90, 103, 216, 0.3);
                }}
                @keyframes fadeIn {{
                    from {{ opacity: 0; transform: translateY(20px); }}
                    to {{ opacity: 1; transform: translateY(0); }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="icon-box">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                </div>
                <h1>Database Suspended</h1>
                <p>Your subscription to this database has expired or been suspended. To restore full access, please renew your subscription by logging into the management portal.</p>
                {"<a href='https://eficienciayproductividadglobal.com/web/login' class='btn'>Renew Subscription</a>" }
            </div>
        </body>
        </html>
        """
        
        return request.make_response(html_content, headers=[('Content-Type', 'text/html')])
