(function () {
  function cleanUrl(url) {
    return String(url || '').replace(/\/+$/, '');
  }

  function enabled() {
    const config = window.NJ_SUPABASE || {};
    return Boolean(config.url && config.anonKey);
  }

  async function insert(table, row) {
    const config = window.NJ_SUPABASE || {};
    if (!enabled()) return { ok: false, skipped: true };
    const response = await fetch(`${cleanUrl(config.url)}/rest/v1/${table}`, {
      method: 'POST',
      headers: {
        apikey: config.anonKey,
        Authorization: `Bearer ${config.anonKey}`,
        'Content-Type': 'application/json',
        Prefer: 'return=minimal',
      },
      body: JSON.stringify(row),
    });
    if (!response.ok) {
      return { ok: false, error: await response.text() };
    }
    return { ok: true };
  }

  async function submitProblemReport(report) {
    return insert('problem_reports', {
      site: report.site || 'NJ Sports Index',
      sport: report.sport || '',
      season: report.season || '',
      page_url: report.pageUrl || window.location.href,
      report_type: report.type || 'Site problem',
      details: report.details || '',
      contact: report.contact || '',
      theme: document.documentElement.dataset.theme || 'dark',
      user_agent: navigator.userAgent,
      metadata: report.metadata || {},
    });
  }

  window.NJSupabaseReports = {
    enabled,
    submit: submitProblemReport,
  };
})();

