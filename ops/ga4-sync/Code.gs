/**
 * MSL GA4 -> Google Sheets sync.
 * GA4 property: 561684830. Sheet: 13gd6ja4npcqHLu5mtPNJMy9u-HJwGPuC50qhRemM8c8.
 * No access tokens or private credentials are stored in this source.
 *
 * First run installDailyMSLSync() interactively in Apps Script. It verifies
 * GA4 access, refreshes data, and installs one daily ~17:00 Pacific trigger.
 */
var MSL_GA4 = Object.freeze({
  property: '561684830',
  spreadsheetId: '13gd6ja4npcqHLu5mtPNJMy9u-HJwGPuC50qhRemM8c8',
  timezone: 'America/Los_Angeles',
  lookbackDays: 28,
  measurementId: 'G-589QHZSK1R'
});

var MSL_METRICS = [
  'sessions', 'activeUsers', 'screenPageViews',
  'engagedSessions', 'bounceRate', 'averageSessionDuration'
];

function installDailyMSLSync() {
  // Do not install a trigger if the credentials/API have not been verified.
  var result = refreshMSLGA4();
  ScriptApp.getProjectTriggers().forEach(function(t) {
    if (t.getHandlerFunction() === 'refreshMSLGA4') ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger('refreshMSLGA4')
    .timeBased().atHour(17).nearMinute(0).everyDays(1)
    .inTimezone(MSL_GA4.timezone).create();
  Logger.log('Daily GA4 sync installed: about 17:00 America/Los_Angeles');
  return result;
}

function refreshMSLGA4() {
  var lock = LockService.getScriptLock();
  if (!lock.tryLock(25000)) throw new Error('Another GA4 sync is in progress.');
  var started = new Date();
  var ss = SpreadsheetApp.openById(MSL_GA4.spreadsheetId);
  var today = Utilities.formatDate(started, MSL_GA4.timezone, 'yyyy-MM-dd');
  var end = shiftIsoDate_(today, -1);
  var start = shiftIsoDate_(end, -(MSL_GA4.lookbackDays - 1));
  try {
    // Fetch every report FIRST. Failure must not erase last known-good data.
    var totals = fetchGa4Rows_(['date'], MSL_METRICS, start, end);
    var pages = fetchGa4Rows_(['date', 'pagePath'], MSL_METRICS, start, end);
    var summary = fetchGa4Rows_(['pagePath'], MSL_METRICS, start, end);
    if (!totals.length) {
      throw new Error('GA4 returned no daily rows. Existing data preserved; check property permissions and dates.');
    }

    var totalRows = totals.map(function(r) {
      var m = r.metrics;
      return [isoDate_(r.dimensions[0]), m[0], m[1], m[2], m[3], m[4], m[5]];
    }).sort(function(a, b) { return a[0].localeCompare(b[0]); });

    var pageRows = pages.map(function(r) {
      var m = r.metrics, path = r.dimensions[1];
      return [isoDate_(r.dimensions[0]), path, versionForPath_(path),
              m[0], m[1], m[2], m[3], m[4], m[5]];
    }).sort(function(a, b) {
      return (a[0] + '|' + a[1]).localeCompare(b[0] + '|' + b[1]);
    });

    var summaryRows = summary.map(function(r) {
      var m = r.metrics, path = r.dimensions[0];
      return [path, versionForPath_(path), m[0], m[1], m[2], m[3]];
    }).sort(function(a, b) { return a[0].localeCompare(b[0]); });

    writeTable_(ss, 'Daily_Total',
      ['date', 'sessions', 'activeUsers', 'screenPageViews',
       'engagedSessions', 'bounceRate', 'avgSessionDurationSec'], totalRows);
    writeTable_(ss, 'Daily_by_Page',
      ['date', 'pagePath', 'version', 'sessions', 'activeUsers',
       'screenPageViews', 'engagedSessions', 'bounceRate', 'avgSessionDurationSec'], pageRows);
    writeTable_(ss, 'Summary_by_Page',
      ['pagePath', 'version', 'sessions', 'activeUsers', 'screenPageViews',
       'engagedSessions'], summaryRows);

    var recordedDates = {};
    totalRows.forEach(function(r) { recordedDates[r[0]] = true; });
    var absentDates = [];
    for (var d = start; d <= end; d = shiftIsoDate_(d, 1)) {
      if (!recordedDates[d]) absentDates.push(d);
    }
    var updated = Utilities.formatDate(new Date(), MSL_GA4.timezone, "yyyy-MM-dd HH:mm:ss z");
    writeDashboard_(ss, updated, start, end, totalRows[totalRows.length - 1][0],
      absentDates, totalRows.length, pageRows.length);

    appendSyncLog_(ss, [updated, 'SUCCESS', start, end,
      totalRows.length, pageRows.length, absentDates.join(', '), '']);
    return {status:'SUCCESS', refreshedAt:updated, lastDataDate:totalRows[totalRows.length - 1][0],
            daysReturned:totalRows.length, missingDateRows:absentDates};
  } catch (e) {
    try {
      appendSyncLog_(ss, [
        Utilities.formatDate(new Date(), MSL_GA4.timezone, 'yyyy-MM-dd HH:mm:ss z'),
        'FAILED', start, end, '', '', '', String(e.message || e)
      ]);
    } catch (logError) {
      Logger.log('Could not write sync error log: ' + logError);
    }
    throw e;
  } finally {
    lock.releaseLock();
  }
}

function fetchGa4Rows_(dimensions, metrics, start, end) {
  var url = 'https://analyticsdata.googleapis.com/v1beta/properties/' +
            MSL_GA4.property + ':runReport';
  var result = [], offset = 0, limit = 10000;
  while (true) {
    var request = {
      dateRanges:[{startDate:start,endDate:end}],
      dimensions:dimensions.map(function(n){return {name:n};}),
      metrics:metrics.map(function(n){return {name:n};}),
      keepEmptyRows:true, offset:String(offset), limit:String(limit),
      orderBys:dimensions.map(function(d){
        return {dimension:{dimensionName:d}, desc:false};
      })
    };
    var response = UrlFetchApp.fetch(url, {
      method:'post', contentType:'application/json',
      headers:{Authorization:'Bearer ' + ScriptApp.getOAuthToken()},
      payload:JSON.stringify(request), muteHttpExceptions:true
    });
    var status = response.getResponseCode();
    var payload = JSON.parse(response.getContentText() || '{}');
    if (status < 200 || status >= 300) {
      throw new Error('GA4 Data API HTTP ' + status + ': ' +
        JSON.stringify(payload.error || payload).substring(0, 1500));
    }
    var rows = payload.rows || [];
    rows.forEach(function(row){
      result.push({
        dimensions:(row.dimensionValues || []).map(function(x){return x.value;}),
        metrics:(row.metricValues || []).map(function(x){return Number(x.value || 0);})
      });
    });
    offset += rows.length;
    if (rows.length === 0 || offset >= Number(payload.rowCount || offset)) break;
  }
  return result;
}

function versionForPath_(path) {
  // Strict canonical paths only. Other hosts' /a/ and /scanner/ are not assumed to match.
  if (path === '/marketing-simulation-lab/a/') return 'A';
  if (path === '/marketing-simulation-lab/scanner/') return 'B';
  return '';
}

function isoDate_(yyyymmdd) {
  if (!/^\d{8}$/.test(yyyymmdd)) throw new Error('Unexpected GA4 date: ' + yyyymmdd);
  return yyyymmdd.substring(0, 4) + '-' + yyyymmdd.substring(4, 6) + '-' +
    yyyymmdd.substring(6, 8);
}

function shiftIsoDate_(date, days) {
  var time = new Date(date + 'T12:00:00Z').getTime() + days * 86400000;
  return new Date(time).toISOString().substring(0, 10);
}

function getOrCreate_(ss, name) {
  return ss.getSheetByName(name) || ss.insertSheet(name);
}

function writeTable_(ss, name, header, rows) {
  var sheet = getOrCreate_(ss, name);
  var values = [header].concat(rows);
  if (sheet.getMaxRows() < values.length) {
    sheet.insertRowsAfter(sheet.getMaxRows(), values.length - sheet.getMaxRows());
  }
  if (sheet.getMaxColumns() < header.length) {
    sheet.insertColumnsAfter(sheet.getMaxColumns(), header.length - sheet.getMaxColumns());
  }
  var oldCount = Math.max(sheet.getLastRow(), 1);
  sheet.getRange(1, 1, oldCount, header.length).clearContent();
  sheet.getRange(1, 1, values.length, header.length).setValues(values);
  sheet.setFrozenRows(1);
}

function writeDashboard_(ss, updated, start, end, latest, absent, dayCount, pageCount) {
  var sheet = getOrCreate_(ss, 'Dashboard');
  var values = [
    ['MSL GA4 — 28-day data freshness', ''],
    ['last_successful_sync_pacific', updated],
    ['query_start', start],
    ['query_end_last_complete_day', end],
    ['latest_date_returned_by_GA4', latest],
    ['days_returned', dayCount],
    ['page_rows_returned', pageCount],
    ['dates_not_returned_by_API', absent.join(', ') || '(none)'],
    ['interpretation', 'Dates not returned are unknown, NOT automatically zero traffic. Recent days may still be provisional.']
  ];
  sheet.getRange(1, 1, Math.max(sheet.getLastRow(), values.length), 2).clearContent();
  sheet.getRange(1, 1, values.length, 2).setValues(values);
  sheet.setColumnWidth(1, 260);
  sheet.setColumnWidth(2, 650);
}

function appendSyncLog_(ss, row) {
  var sheet = getOrCreate_(ss, 'Sync_Log');
  if (sheet.getLastRow() === 0) {
    sheet.appendRow(['timestamp_pacific', 'status', 'from_date', 'through_date',
                     'daily_rows', 'page_rows', 'dates_not_returned', 'error']);
  }
  sheet.appendRow(row);
}
