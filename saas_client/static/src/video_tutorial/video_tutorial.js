/** @odoo-module **/

import { Component, useState, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

export class VideoTutorialSystray extends Component {
    setup() {
        this.menuService = useService("menu");
        this.state = useState({ tick: 0 });
        
        // Listen to URL hash changes so we know when the user switches apps
        window.addEventListener('hashchange', () => {
            this.state.tick++;
        });
        
        onMounted(() => {
            // Force re-evaluate after mount so if they loaded directly into an app, it shows
            setTimeout(() => { this.state.tick++; }, 500);
        });
    }

    get currentAppVideo() {
        // Access state.tick to ensure Owl tracks it as a dependency for re-rendering
        const _trigger = this.state.tick;
        const currentApp = this.menuService.getCurrentApp();
        if (!currentApp) return null;
        
        const xmlid = (currentApp.xmlid || '').toLowerCase();
        const name = (currentApp.name || '').toLowerCase();

        // Fuzzy matching to ensure we catch the correct app regardless of translation or custom XML IDs
        if (xmlid.includes('base_setup') || name.includes('settings') || name.includes('ajuste')) {
            return {
                'en': 'https://youtu.be/1qerqEWq9Ts?si=67gT8Iw2JzCxIuDe',
                'es': 'https://youtu.be/pAPDDab1c8E?si=rWOXpPY7MrHg5QvM'
            };
        }
        if (xmlid.includes('sale') || name.includes('sale') || name.includes('venta')) {
            return {
                'en': 'https://youtu.be/QVZW-1Fq3p8?si=oHHThXdZosgwGi1U',
                'es': 'https://youtu.be/7X6dKUsBUQA?si=3T_FGecoOrxUBDNt'
            };
        }
        if (xmlid.includes('crm') || name.includes('crm') || name.includes('fujo')) {
            return {
                'en': 'https://youtu.be/t9etMxFIlvM?si=UCQV6wRCIwsdkJmV',
                'es': 'https://youtu.be/-ISd_42GlOo?si=06H0wtKGS8Q95ofs'
            };
        }
        if (xmlid.includes('document') || name.includes('document')) {
            return {
                'en': 'https://youtu.be/vq4oL9jZvRw?si=vCHKgqNoNCyyLe5i',
                'es': 'https://youtu.be/BUSkqDMWZzI?si=2ZjI1C6es9c3n65S'
            };
        }
        if (xmlid.includes('board') || name.includes('dashboard') || name.includes('tablero')) {
            return {
                'en': 'https://youtu.be/-GCIGDN6HvQ?si=DlK-UjMzItCAehL0',
                'es': 'https://youtu.be/ZPJnHJXpxNo?si=maQiiOqb56to9ga0'
            };
        }
        if (xmlid.includes('contact') || name.includes('contact')) {
            return {
                'en': 'https://youtu.be/PyCsLvbiCWM?si=5UJ1WGsbUFuWDh6O',
                'es': 'https://youtu.be/DHzvmNPsN_U?si=gqIGM4t2w5XkT8Nk'
            };
        }
        if (xmlid.includes('ai') || name.includes('ai') || name.includes('assistant') || name.includes('inteligencia') || name.includes('robot')) {
            return {
                'en': 'https://youtu.be/Hzkyzx9Jzk8?si=ZjVWHb6t-OJaSZO0',
                'es': 'https://youtu.be/JZjbb-0Cq6I?si=R_CVW8q8R-Qw8JCv'
            };
        }
        if (xmlid.includes('account') || name.includes('account') || name.includes('contabilidad') || name.includes('finance') || name.includes('facturaci')) {
            return {
                'en': 'https://youtu.be/tSj9QFVUt2k?si=fJdd2QI2yUpcMFOP',
                'es': 'https://youtu.be/iEFSQXn1rUA?si=O8bfE7F-6Z0lpFTG'
            };
        }
        
        return null;
    }

    get isVisible() {
        return this.currentAppVideo !== null;
    }

    openVideo(lang) {
        const video = this.currentAppVideo;
        if (video && video[lang]) {
            window.open(video[lang], '_blank');
        }
    }
}

VideoTutorialSystray.template = "saas_client.VideoTutorialSystray";
VideoTutorialSystray.components = { Dropdown, DropdownItem };

export const systrayItem = {
    Component: VideoTutorialSystray,
    isDisplayed: (env) => true,
};

registry.category("systray").add("VideoTutorialSystray", systrayItem, { sequence: 98 });
