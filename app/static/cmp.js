(function () {
  "use strict";

  var VISITOR_REF_STORAGE_KEY = "cmp_visitor_ref";

  var script = document.currentScript;
  var scriptSrc = (script && script.src) || "";
  var apiBase = scriptSrc.replace(/\/(api(?:\/v\d+)?\/)?sdk\/cmp\.js(\?.*)?$/, "");
  var API_PREFIX = "/v1";

  function fetchJson(url, options) {
    return fetch(url, options).then(function (response) {
      return response.json().catch(function () { return {}; }).then(function (payload) {
        if (!response.ok) {
          var msg = payload && payload.message ? String(payload.message) : "Request failed";
          throw new Error(msg);
        }
        var status = payload && payload.status ? String(payload.status).toLowerCase() : "";
        if (status === "fail" || status === "error") {
          var apiMsg = payload && payload.message ? String(payload.message) : "Request failed";
          throw new Error(apiMsg);
        }
        return payload;
      });
    });
  }

  function getConfig(domain) {
    return fetchJson(apiBase + API_PREFIX + "/sdk/config?domain=" + encodeURIComponent(domain), {
      method: "GET",
      credentials: "omit",
    });
  }

  function createSession(domain) {
    return fetchJson(apiBase + API_PREFIX + "/runtime/sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ domain: domain }),
    });
  }

  function saveConsent(payload, token) {
    return fetchJson(apiBase + API_PREFIX + "/consents/create", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: "Bearer " + token,
      },
      body: JSON.stringify(payload),
    });
  }

  function getCurrentConsent(templateId, domain, visitorRef) {
    var query =
      "?template_id=" +
      encodeURIComponent(templateId) +
      "&domain=" +
      encodeURIComponent(domain) +
      "&visitor_ref=" +
      encodeURIComponent(visitorRef);
    return fetchJson(apiBase + API_PREFIX + "/sdk/consents/current" + query, {
      method: "GET",
      credentials: "omit",
    });
  }

  function getOrCreateVisitorRef() {
    try {
      var existing = localStorage.getItem(VISITOR_REF_STORAGE_KEY);
      if (existing) {
        var trimmed = String(existing).trim();
        if (trimmed.length > 0) {
          return trimmed.length > 255 ? trimmed.slice(0, 255) : trimmed;
        }
      }
    } catch (_e) {}
    var id;
    try {
      if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
        id = crypto.randomUUID();
      }
    } catch (_e2) {}
    if (!id) {
      id =
        "vis_" +
        Date.now().toString(36) +
        "_" +
        Math.random().toString(36).slice(2, 14);
    }
    id = String(id);
    if (id.length > 255) {
      id = id.slice(0, 255);
    }
    try {
      localStorage.setItem(VISITOR_REF_STORAGE_KEY, id);
    } catch (_e3) {}
    return id;
  }

  window.CMP = {
    getConfig: getConfig,
    createSession: createSession,
    saveConsent: saveConsent,
    getCurrentConsent: getCurrentConsent,
    getVisitorRef: getOrCreateVisitorRef,
  };
})();
