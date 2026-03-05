/** @odoo-module **/

/**
 * CRM Client Kanban – JS helpers
 *
 * The "New Deal" button calls `action_new_opportunity` on res.partner.
 * We add that server action via data/server_actions.xml (optional).
 * This file adds any extra interactivity needed on the kanban cards.
 */

import { patch } from "@web/core/utils/patch";
import { KanbanRecord } from "@web/views/kanban/kanban_record";

patch(KanbanRecord.prototype, {
    /**
     * Intercept the "type=edit" button on our custom card so it opens
     * the partner form in edit mode directly.
     */
    async onGlobalClick(ev) {
        // Let default behaviour run for our custom buttons
        if (ev.target.closest(".ckd_btn_edit") || ev.target.closest(".ckd_btn_deal")) {
            return;
        }
        return super.onGlobalClick(ev);
    },
});
