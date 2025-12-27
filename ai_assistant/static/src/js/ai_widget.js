/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class AiAssistantWidget extends Component {
    static template = "ai_assistant.AiAssistantWidget";
    
    setup() {
        super.setup();
        
        // Initialize reactive state
        this.state = useState({
            isOpen: false,
            messages: [],
            inputText: "",
            isLoading: false,
            unreadCount: 0,
            currentContext: null,
            isConfigured: false,
        });
        
        // Get Odoo services
        this.actionService = useService("action");
        this.notificationService = useService("notification");
        
        // Load previous messages
        this._loadMessagesFromStorage();
        
        // Check configuration on start
        onWillStart(async () => {
            await this._checkConfiguration();
        });
        
        // Listen for action changes to update context
        this._setupContextListener();
    }
    
    async _checkConfiguration() {
        try {
            const config = await rpc("/ai/config", {});
            this.state.isConfigured = config.configured;
            
            if (!this.state.isConfigured) {
                this.state.messages.push({
                    text: "⚠️ AI Assistant is not configured. Please set up your API key in System Parameters.",
                    sender: "system",
                    timestamp: new Date(),
                    isWarning: true,
                });
            }
        } catch (error) {
            console.error("Failed to check configuration:", error);
        }
    }
    
    _setupContextListener() {
        // Update context when action changes
        if (this.actionService) {
            const updateContext = () => {
                this._updateCurrentContext();
            };
            
            // Listen for action changes
            // Note: In Odoo 18, we need to check the current controller
            setInterval(() => this._updateCurrentContext(), 3000);
        }
    }
    
    _updateCurrentContext() {
        try {
            const actionManager = this.actionService;
            if (actionManager && actionManager.currentController) {
                const current = actionManager.currentController.props;
                if (current && current.resModel && current.resId) {
                    this.state.currentContext = {
                        model: current.resModel,
                        id: current.resId,
                        name: current.display_name || current.name || "Record",
                    };
                    return;
                }
            }
            
            // Fallback: check URL
            const urlParams = new URLSearchParams(window.location.search);
            const model = urlParams.get('model');
            const id = urlParams.get('id');
            
            if (model && id) {
                this.state.currentContext = {
                    model: model,
                    id: parseInt(id),
                    name: "Current Record",
                };
            } else {
                this.state.currentContext = null;
            }
        } catch (error) {
            console.warn("Failed to update context:", error);
            this.state.currentContext = null;
        }
    }
    
    toggleWidget() {
        this.state.isOpen = !this.state.isOpen;
        
        if (this.state.isOpen) {
            // Reset unread count when opening
            this.state.unreadCount = 0;
            this._saveMessagesToStorage();
            
            // Update context when opening
            this._updateCurrentContext();
            
            // Auto-scroll to bottom
            setTimeout(() => this._scrollToBottom(), 100);
        }
    }
    
    async sendMessage() {
        const question = this.state.inputText.trim();
        if (!question || this.state.isLoading || !this.state.isConfigured) {
            if (!this.state.isConfigured) {
                this.notificationService.add(
                    "Please configure API key in System Parameters first.",
                    { type: "warning" }
                );
            }
            return;
        }
        
        // Add user message
        this.state.messages.push({
            text: question,
            sender: "user",
            timestamp: new Date(),
            id: `user_${Date.now()}`,
        });
        
        this.state.inputText = "";
        this.state.isLoading = true;
        
        // Auto-scroll
        this._scrollToBottom();
        
        try {
            // Get current context
            const context = this.state.currentContext;
            
            // Call AI endpoint
            const response = await rpc("/ai/ask", {
                question: question,
                active_model: context ? context.model : null,
                active_id: context ? context.id : null,
            });
            
            if (response.success) {
                // Add AI response
                this.state.messages.push({
                    text: response.answer,
                    sender: "ai",
                    timestamp: new Date(),
                    id: `ai_${Date.now()}`,
                });
                
                this.notificationService.add(
                    "🤖 AI response received",
                    { type: "success" }
                );
            } else {
                // Show error
                this.state.messages.push({
                    text: response.answer || "❌ Sorry, I encountered an error.",
                    sender: "ai",
                    timestamp: new Date(),
                    id: `error_${Date.now()}`,
                    isError: true,
                });
                
                this.notificationService.add(
                    response.answer || "AI Error",
                    { type: "danger" }
                );
            }
        } catch (error) {
            console.error("AI Assistant Error:", error);
            
            this.state.messages.push({
                text: "🌐 Network error. Please check your connection and try again.",
                sender: "ai",
                timestamp: new Date(),
                id: `network_${Date.now()}`,
                isError: true,
            });
            
            this.notificationService.add(
                "Network error - please try again",
                { type: "danger" }
            );
        } finally {
            this.state.isLoading = false;
            
            // Save messages
            this._saveMessagesToStorage();
            
            // Update unread count if widget is closed
            if (!this.state.isOpen) {
                this.state.unreadCount++;
            }
            
            // Auto-scroll to bottom
            this._scrollToBottom();
        }
    }
    
    handleKeyPress(ev) {
        if (ev.key === "Enter" && !ev.shiftKey) {
            ev.preventDefault();
            this.sendMessage();
        }
    }
    
    clearChat() {
        if (confirm("Are you sure you want to clear the chat history?")) {
            this.state.messages = [];
            localStorage.removeItem("ai_assistant_messages");
            this.state.unreadCount = 0;
            this.notificationService.add(
                "Chat history cleared",
                { type: "info" }
            );
        }
    }
    
    async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            this.notificationService.add(
                "📋 Copied to clipboard",
                { type: "info" }
            );
        } catch (err) {
            console.error("Failed to copy:", err);
            this.notificationService.add(
                "Failed to copy to clipboard",
                { type: "warning" }
            );
        }
    }
    
    retryLastMessage() {
        if (this.state.messages.length > 0) {
            const lastUserMessage = [...this.state.messages]
                .reverse()
                .find(msg => msg.sender === "user");
            
            if (lastUserMessage) {
                this.state.inputText = lastUserMessage.text;
                setTimeout(() => {
                    const input = document.querySelector(".ai-input");
                    if (input) input.focus();
                }, 100);
            }
        }
    }
    
    _saveMessagesToStorage() {
        try {
            // Keep only last 50 messages to avoid storage issues
            const messagesToSave = this.state.messages
                .filter(msg => msg.sender !== "system") // Don't save system messages
                .slice(-50)
                .map(msg => ({
                    text: msg.text,
                    sender: msg.sender,
                    timestamp: msg.timestamp.toISOString(),
                }));
            
            localStorage.setItem(
                "ai_assistant_messages", 
                JSON.stringify(messagesToSave)
            );
        } catch (error) {
            console.warn("Failed to save messages to localStorage:", error);
        }
    }
    
    _loadMessagesFromStorage() {
        try {
            const saved = localStorage.getItem("ai_assistant_messages");
            if (saved) {
                const messages = JSON.parse(saved).map(msg => ({
                    ...msg,
                    timestamp: new Date(msg.timestamp),
                    id: `loaded_${Date.now()}_${Math.random()}`,
                }));
                
                // Only load if we don't have current messages
                if (this.state.messages.length === 0) {
                    this.state.messages = messages;
                }
            }
        } catch (error) {
            console.warn("Failed to load messages from localStorage:", error);
        }
    }
    
    _scrollToBottom() {
        setTimeout(() => {
            const messagesContainer = this.el?.querySelector(".ai-messages");
            if (messagesContainer) {
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
            }
        }, 100);
    }
    
    get contextInfo() {
        if (!this.state.currentContext) {
            return "No specific context";
        }
        
        const { model, name } = this.state.currentContext;
        const modelNames = {
            'crm.lead': 'CRM Lead',
            'res.partner': 'Contact',
            'project.task': 'Task',
            'sale.order': 'Sales Order',
            'account.move': 'Invoice',
        };
        
        const friendlyModel = modelNames[model] || model;
        return `${friendlyModel}: ${name}`;
    }
}

// Widget configuration
AiAssistantWidget.props = {};

// Add to systray
export const aiAssistantSystrayItem = {
    Component: AiAssistantWidget,
};

registry.category("systray").add("ai_assistant.widget", aiAssistantSystrayItem);