from odoo import http
from odoo.http import request
import json
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)

class AiAssistantController(http.Controller):
    
    @http.route("/ai/ask", type="json", auth="user", methods=["POST"], csrf=False)
    def ai_ask(self, question, active_model=None, active_id=None, **kwargs):
        """
        Main endpoint for AI queries with context awareness.
        """
        try:
            _logger.info(f"AI Request - Question: '{question[:100]}...', Model: {active_model}, ID: {active_id}")
            
            user = request.env.user
            
            # Get or create assistant for this user
            assistant = request.env["ai.assistant"].search([
                ("user_id", "=", user.id),
                ("active", "=", True)
            ], limit=1, order="create_date desc")
            
            if not assistant:
                assistant = request.env["ai.assistant"].create({
                    "user_id": user.id,
                    "name": f"{user.name}'s AI Assistant"
                })
            
            # Get detailed context from the active record
            context_data = self._get_record_context(active_model, active_id)
            _logger.debug(f"Context for AI: {context_data[:500]}")
            
            # Call the LLM with question and context
            answer = assistant.call_external_llm(question, context_data)
            
            # Store the conversation
            message = request.env["ai.message"].create({
                "assistant_id": assistant.id,
                "question": question,
                "answer": answer,
                "model_context": active_model,
                "record_id": active_id,
                "timestamp": datetime.now(),
            })
            
            _logger.info(f"AI Response stored: ID {message.id}")
            
            return {
                "success": True,
                "answer": answer,
                "message_id": message.id,
                "timestamp": message.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            }
            
        except Exception as e:
            _logger.error(f"Error in ai_ask: {str(e)}", exc_info=True)
            return {
                "success": False,
                "answer": f"❌ Error: {str(e)}",
                "error": str(e),
            }
    
    def _get_record_context(self, model_name, record_id):
        """
        Extract meaningful context from the current Odoo record.
        """
        if not model_name or not record_id:
            return "No specific record is currently active. General context mode."
        
        try:
            # Safely get the model
            if model_name not in request.env:
                return f"Unknown model type: {model_name}"
            
            model = request.env[model_name]
            record = model.browse(int(record_id))
            
            if not record.exists():
                return f"The {model_name} record (ID: {record_id}) no longer exists."
            
            # Check if user has read access
            try:
                record.check_access_rights("read")
                record.check_access_rule("read")
            except:
                return f"You don't have permission to view this {model_name} record."
            
            # Extract context based on model type
            context_lines = []
            
            if model_name == "crm.lead":
                context_lines = self._extract_crm_lead_context(record)
            elif model_name == "res.partner":
                context_lines = self._extract_partner_context(record)
            elif model_name == "project.task":
                context_lines = self._extract_task_context(record)
            elif model_name == "sale.order":
                context_lines = self._extract_sale_order_context(record)
            elif model_name == "account.move":
                context_lines = self._extract_invoice_context(record)
            else:
                context_lines = self._extract_generic_context(record, model_name)
            
            # Add header
            header = f"=== CURRENT RECORD CONTEXT ===\n"
            header += f"Model: {model_name}\n"
            header += f"Record ID: {record_id}\n"
            
            context = header + "\n".join(context_lines)
            return context
            
        except Exception as e:
            _logger.warning(f"Failed to extract context for {model_name}/{record_id}: {str(e)}")
            return f"Could not load detailed context for {model_name}. Error: {str(e)}"
    
    def _extract_crm_lead_context(self, lead):
        """Extract CRM lead specific information."""
        context = []
        
        # Basic info
        context.append(f"📋 Lead/Opportunity: {lead.name or 'Unnamed'}")
        
        if lead.partner_id:
            context.append(f"👤 Customer: {lead.partner_id.name}")
            if lead.partner_id.email:
                context.append(f"   📧 Email: {lead.partner_id.email}")
            if lead.partner_id.phone:
                context.append(f"   📞 Phone: {lead.partner_id.phone}")
        
        if lead.description:
            desc = lead.description.replace('\n', ' ').strip()[:200]
            context.append(f"📝 Description: {desc}...")
        
        if lead.stage_id:
            context.append(f"🎯 Stage: {lead.stage_id.name}")
        
        if lead.expected_revenue:
            context.append(f"💰 Expected Revenue: ${lead.expected_revenue:,.2f}")
        
        if lead.priority:
            priority_map = {"0": "Low", "1": "Medium", "2": "High", "3": "Very High"}
            priority = priority_map.get(lead.priority, lead.priority)
            context.append(f"⚡ Priority: {priority}")
        
        if lead.type:
            opp_type = "Opportunity" if lead.type == "opportunity" else "Lead"
            context.append(f"🔧 Type: {opp_type}")
        
        if lead.user_id:
            context.append(f"👨‍💼 Salesperson: {lead.user_id.name}")
        
        if lead.create_date:
            create_date = lead.create_date.strftime("%Y-%m-%d")
            context.append(f"📅 Created: {create_date}")
        
        # Custom fields
        if hasattr(lead, 'source_id') and lead.source_id:
            context.append(f"📡 Source: {lead.source_id.name}")
        
        if hasattr(lead, 'campaign_id') and lead.campaign_id:
            context.append(f"🎯 Campaign: {lead.campaign_id.name}")
        
        return context
    
    def _extract_partner_context(self, partner):
        """Extract partner/contact information."""
        context = []
        
        context.append(f"👤 Contact: {partner.name or 'Unnamed'}")
        
        if partner.email:
            context.append(f"📧 Email: {partner.email}")
        
        if partner.phone:
            context.append(f"📞 Phone: {partner.phone}")
        
        if partner.parent_id:
            context.append(f"🏢 Company: {partner.parent_id.name}")
        
        if partner.category_id:
            categories = ", ".join(partner.category_id.mapped('name'))
            context.append(f"🏷️ Tags: {categories}")
        
        if partner.street:
            address = f"{partner.street or ''}"
            if partner.city:
                address += f", {partner.city}"
            if partner.country_id:
                address += f", {partner.country_id.name}"
            context.append(f"📍 Address: {address}")
        
        if partner.comment:
            comment = partner.comment.replace('\n', ' ').strip()[:150]
            context.append(f"📝 Notes: {comment}...")
        
        return context
    
    def _extract_generic_context(self, record, model_name):
        """Extract generic information from any record."""
        context = []
        
        # Always try to get name
        if hasattr(record, 'name') and record.name:
            context.append(f"📄 Record: {record.name}")
        
        # Try common fields
        common_fields = {
            'description': '📝 Description',
            'notes': '📝 Notes',
            'summary': '📋 Summary',
            'subject': '📌 Subject',
            'title': '🏷️ Title',
            'code': '🔢 Code',
            'reference': '🔗 Reference',
            'state': '📊 State',
            'status': '📊 Status',
        }
        
        for field, label in common_fields.items():
            if hasattr(record, field) and getattr(record, field):
                value = str(getattr(record, field))
                if len(value) > 100:
                    value = value[:100] + "..."
                context.append(f"{label}: {value}")
        
        # Get create date if available
        if hasattr(record, 'create_date') and record.create_date:
            create_date = record.create_date.strftime("%Y-%m-%d")
            context.append(f"📅 Created: {create_date}")
        
        return context if context else [f"No extractable context from {model_name} record."]
    
    @http.route("/ai/health", type="json", auth="user", methods=["POST"])
    def health_check(self, **kwargs):
        """Health check endpoint."""
        return {
            "status": "healthy",
            "version": "1.0",
            "timestamp": datetime.now().isoformat(),
        }
    
    @http.route("/ai/config", type="json", auth="user", methods=["POST"])
    def get_config(self, **kwargs):
        """Get current AI configuration."""
        api_key = request.env["ir.config_parameter"].sudo().get_param("ai_assistant.api_key")
        endpoint = request.env["ir.config_parameter"].sudo().get_param("ai_assistant.endpoint")
        
        return {
            "has_api_key": bool(api_key and api_key.strip()),
            "endpoint": endpoint or "Not configured",
            "configured": bool(api_key and api_key.strip() and endpoint and endpoint.strip()),
        }