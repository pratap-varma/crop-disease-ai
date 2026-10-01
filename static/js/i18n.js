// =============================================================
// i18n.js  —  Native Client-Side Translation Engine
// =============================================================

(function () {
    "use strict";

    const SUPPORTED_LANGUAGES = {
        en: "English",
        te: "తెలుగు",
        hi: "हिन्दी",
        ta: "தமிழ்",
        kn: "ಕನ್ನಡ",
        ml: "മലയാളം",
        mr: "मराठी",
        bn: "বাংলা",
        gu: "ગુજરાતી",
        pa: "ਪੰਜਾਬੀ",
        or: "ଓଡ଼ିଆ"
    };

    let currentTranslations = {};
    let fallbackTranslations = {};
    let reverseMap = {};

    function normalizeText(str) {
        if (!str) return "";
        return str.replace(/\s+/g, ' ').trim().toLowerCase();
    }

    /**
     * Build a reverse map from English translation values to their keys
     */
    function buildReverseMap() {
        reverseMap = {};
        Object.entries(fallbackTranslations).forEach(([key, val]) => {
            if (typeof val === "string") {
                reverseMap[normalizeText(val)] = key;
            }
        });
    }

    function findKeyByText(text) {
        const norm = normalizeText(text);
        return reverseMap[norm] || null;
    }

    /**
     * Load language file (from sessionStorage cache or via fetch)
     */
    async function loadLanguage(lang) {
        const cacheKey = `i18n_cache_${lang}`;
        const cached = sessionStorage.getItem(cacheKey);
        
        if (cached) {
            try {
                const data = JSON.parse(cached);
                // Validate cached data has the new keys, if not clear cache
                if (data && data["about.sujana_role"]) {
                    return data;
                }
                sessionStorage.removeItem(cacheKey);
            } catch (e) {
                console.error("Error parsing cached translations:", e);
            }
        }

        try {
            const res = await fetch(`/translations/${lang}.json`);
            if (res.ok) {
                const data = await res.json();
                sessionStorage.setItem(cacheKey, JSON.stringify(data));
                return data;
            }
        } catch (e) {
            console.error(`Error fetching translation file for ${lang}:`, e);
        }
        return null;
    }

    /**
     * Set up translation dictionary and fallback dictionary
     */
    async function initI18n() {
        const selectedLang = localStorage.getItem("selectedLang") || "en";
        
        // Load fallback (English) first to build the reverse map
        fallbackTranslations = await loadLanguage("en") || {};
        buildReverseMap();
        
        if (selectedLang === "en") {
            currentTranslations = fallbackTranslations;
        } else {
            currentTranslations = await loadLanguage(selectedLang) || {};
        }

        applyDOMTranslations();
        
        document.dispatchEvent(new CustomEvent("i18n-ready", { detail: { language: selectedLang } }));
    }

    /**
     * Translate a key, falling back to English, then back to key name
     */
    function translate(key, defaultVal) {
        if (currentTranslations && currentTranslations[key]) {
            return currentTranslations[key];
        }
        if (fallbackTranslations && fallbackTranslations[key]) {
            return fallbackTranslations[key];
        }
        if (defaultVal !== undefined) {
            return defaultVal;
        }
        console.warn(`Missing translation key: ${key}`);
        return key;
    }

    /**
     * Walks DOM text nodes and replaces matching English text with target translation.
     * Preserves elements, attributes, and structures.
     */
    function translateTextNode(node) {
        if (node.nodeType !== Node.TEXT_NODE) return;
        
        const originalText = node.getAttribute ? node.getAttribute("data-i18n-orig") : node.nodeValue;
        const textVal = originalText || node.nodeValue;
        if (!textVal || !textVal.trim()) return;

        // Skip translation for already translated non-English text to prevent double-translation
        const selectedLang = localStorage.getItem("selectedLang") || "en";
        
        // Save original English text if not saved yet
        if (node.nodeType === Node.TEXT_NODE && !node.parentI18nOrigSet) {
            node.parentI18nOrigVal = textVal;
            node.parentI18nOrigSet = true;
        }

        const lookupText = node.parentI18nOrigVal;
        const key = findKeyByText(lookupText);

        if (key) {
            const translatedText = translate(key);
            // Preserve leading/trailing whitespace of the original node value
            const lead = lookupText.match(/^\s*/)[0];
            const trail = lookupText.match(/\s*$/)[0];
            node.nodeValue = lead + translatedText.trim() + trail;
        }
    }

    function walk(node) {
        // Skip script, style, and iframe tags
        const skipTags = ["SCRIPT", "STYLE", "IFRAME"];
        if (node.nodeType === Node.ELEMENT_NODE && skipTags.includes(node.tagName)) {
            return;
        }

        // Handle placeholders for input and textarea
        if (node.nodeType === Node.ELEMENT_NODE && (node.tagName === "INPUT" || node.tagName === "TEXTAREA")) {
            const placeholder = node.getAttribute("placeholder");
            if (placeholder) {
                if (!node.hasAttribute("data-i18n-orig-placeholder")) {
                    node.setAttribute("data-i18n-orig-placeholder", placeholder);
                }
                const origPlac = node.getAttribute("data-i18n-orig-placeholder");
                const key = findKeyByText(origPlac);
                if (key) {
                    node.setAttribute("placeholder", translate(key));
                }
            }
        }

        // Process text nodes
        if (node.nodeType === Node.TEXT_NODE) {
            translateTextNode(node);
        } else {
            for (let child = node.firstChild; child; child = child.nextSibling) {
                walk(child);
            }
        }
    }

    /**
     * Recursively walk the DOM and translate elements
     */
    function applyDOMTranslations() {
        walk(document.body);

        const selectedLang = localStorage.getItem("selectedLang") || "en";
        
        // Update document lang attribute
        document.documentElement.setAttribute("lang", selectedLang);
        
        document.dispatchEvent(new CustomEvent("i18n-applied", { detail: { language: selectedLang } }));
    }

    /**
     * Change language immediately without reloading
     */
    async function changeLanguage(langCode) {
        if (!SUPPORTED_LANGUAGES[langCode]) {
            console.error(`Unsupported language code: ${langCode}`);
            return;
        }

        localStorage.setItem("selectedLang", langCode);
        
        // Set cookie so backend knows the language code
        document.cookie = "selected_lang=" + langCode + "; path=/; max-age=31536000";
        
        const data = await loadLanguage(langCode);
        if (data) {
            currentTranslations = data;
        } else {
            currentTranslations = fallbackTranslations;
        }

        applyDOMTranslations();
    }

    window.i18n = {
        SUPPORTED_LANGUAGES,
        translate,
        changeLanguage,
        init: initI18n,
        apply: applyDOMTranslations
    };
    
    window.translate = translate;

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initI18n);
    } else {
        initI18n();
    }
})();
