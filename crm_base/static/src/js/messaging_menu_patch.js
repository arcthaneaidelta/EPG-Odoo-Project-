/** @odoo-module **/

import { MessagingMenu } from "@mail/core/public_web/messaging_menu";
import { patch } from "@web/core/utils/patch";

patch(MessagingMenu.prototype, {
    get canPromptToInstall() {
        // Always return false to disable the "Come here often? Install Odoo" chat message
        return false;
    }
});
