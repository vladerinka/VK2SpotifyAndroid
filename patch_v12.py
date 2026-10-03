from pathlib import Path
root=Path('VK2SpotifyAndroid')
p=root/'app/src/main/java/com/vk2spotify/transfer/MainActivity.java'
s=p.read_text(encoding='utf-8')

s=s.replace('''    private ProgressBar transferProgress;\n''','''    private ProgressBar transferProgress;\n    private TextView quotaStatusText;\n    private TextView quotaDetailText;\n    private ProgressBar quotaProgress;\n''',1)

s=s.replace('''        root.addView(spotifyCard());\n        root.addView(destinationCard());''','''        root.addView(spotifyCard());\n        root.addView(quotaCard());\n        root.addView(destinationCard());''',1)

s=s.replace('''        updateTrackCount();\n        updateReadiness();\n''','''        updateTrackCount();\n        updateReadiness();\n        updateQuotaUi();\n''',1)

s=s.replace('VK MUSIC  →  SPOTIFY   •   v1.1','VK MUSIC  →  SPOTIFY   •   v1.2',1)

needle='''    private View destinationCard() {\n'''
quota_card=r'''    private View quotaCard() {
        LinearLayout box = cardBox();
        box.addView(cardTop("Квота Spotify", "Development Mode", danger));

        TextView warning = label("⚠ Spotify ограничивает API-квоту. Фиксированное число треков в день Spotify не публикует.", 13, text, Typeface.BOLD);
        warning.setLineSpacing(0, 1.12f);
        warning.setPadding(0, dp(7), 0, dp(9));
        box.addView(warning);

        quotaStatusText = label("Считаю использование…", 14, text, Typeface.BOLD);
        quotaStatusText.setPadding(0, 0, 0, dp(7));
        box.addView(quotaStatusText);

        quotaProgress = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        quotaProgress.setMax(1000);
        quotaProgress.setProgress(0);
        if (android.os.Build.VERSION.SDK_INT >= 21) {
            quotaProgress.setProgressTintList(ColorStateList.valueOf(primary));
            quotaProgress.setProgressBackgroundTintList(ColorStateList.valueOf(border));
        }
        box.addView(quotaProgress, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dp(8)));

        quotaDetailText = label("Стартовая оценка: ≈400 поисков треков на окно квоты. После реального QUOTA_EXCEEDED приложение уточнит её автоматически.", 12, muted, Typeface.NORMAL);
        quotaDetailText.setPadding(0, dp(8), 0, 0);
        quotaDetailText.setLineSpacing(0, 1.12f);
        box.addView(quotaDetailText);
        return box;
    }

'''
if needle not in s:
    raise SystemExit('destination insertion point not found')
s=s.replace(needle,quota_card+needle,1)

old='''    private String findSpotifyTrack(Track target) throws Exception {\n        Uri uri = Uri.parse("https://api.spotify.com/v1/search").buildUpon()'''
new='''    private String findSpotifyTrack(Track target) throws Exception {\n        recordQuotaSearch();\n        Uri uri = Uri.parse("https://api.spotify.com/v1/search").buildUpon()'''
if old not in s:
    raise SystemExit('findSpotifyTrack insertion point not found')
s=s.replace(old,new,1)

old='''            if("QUOTA_EXCEEDED".equalsIgnoreCase(reason)||wait>300)throw new SpotifyQuotaExceeded(wait);'''
new='''            if("QUOTA_EXCEEDED".equalsIgnoreCase(reason)||wait>300){ noteQuotaExceeded(wait); throw new SpotifyQuotaExceeded(wait); }'''
if old not in s:
    raise SystemExit('quota exceeded insertion point not found')
s=s.replace(old,new,1)

needle='''    private HttpResult spotifyRequest(String method, String url, String body) throws Exception {\n'''
helpers=r'''    private void normalizeQuotaWindow() {
        long now = System.currentTimeMillis();
        long until = prefs.getLong("spotify_quota_until", 0L);
        long started = prefs.getLong("quota_window_started_at", 0L);
        boolean knownReset = until > 0L && now >= until;
        boolean staleEstimateWindow = until == 0L && started > 0L && now - started > 26L * 60L * 60L * 1000L;
        if (knownReset || staleEstimateWindow) {
            prefs.edit()
                    .putInt("quota_track_searches_used", 0)
                    .putLong("quota_window_started_at", now)
                    .remove("spotify_quota_until")
                    .apply();
        }
    }

    private void recordQuotaSearch() {
        normalizeQuotaWindow();
        long now = System.currentTimeMillis();
        int used = prefs.getInt("quota_track_searches_used", 0) + 1;
        SharedPreferences.Editor e = prefs.edit().putInt("quota_track_searches_used", used);
        if (prefs.getLong("quota_window_started_at", 0L) == 0L) e.putLong("quota_window_started_at", now);
        e.apply();
        if (used == 1 || used % 5 == 0) runOnUiThread(this::updateQuotaUi);
    }

    private void noteQuotaExceeded(int retryAfterSeconds) {
        long now = System.currentTimeMillis();
        long until = now + Math.max(60, retryAfterSeconds) * 1000L;
        int used = prefs.getInt("quota_track_searches_used", 0);
        int oldEstimate = Math.max(50, prefs.getInt("quota_estimated_capacity", 400));
        int learned = oldEstimate;
        if (used >= 50 && used <= 5000) learned = used;
        prefs.edit()
                .putLong("spotify_quota_until", until)
                .putInt("quota_estimated_capacity", learned)
                .apply();
        runOnUiThread(this::updateQuotaUi);
    }

    private void updateQuotaUi() {
        if (quotaStatusText == null || quotaProgress == null || quotaDetailText == null) return;
        normalizeQuotaWindow();
        int used = Math.max(0, prefs.getInt("quota_track_searches_used", 0));
        int estimate = Math.max(50, prefs.getInt("quota_estimated_capacity", 400));
        long now = System.currentTimeMillis();
        long until = prefs.getLong("spotify_quota_until", 0L);
        boolean exhausted = until > now;

        int progress = Math.min(1000, (int) Math.round(used * 1000.0 / estimate));
        if (exhausted) progress = 1000;
        quotaProgress.setProgress(progress);
        if (android.os.Build.VERSION.SDK_INT >= 21) {
            quotaProgress.setProgressTintList(ColorStateList.valueOf(exhausted ? danger : primary));
        }

        if (exhausted) {
            long left = Math.max(0L, until - now);
            long totalMinutes = (left + 59999L) / 60000L;
            long hours = totalMinutes / 60L;
            long minutes = totalMinutes % 60L;
            quotaStatusText.setText("Квота исчерпана • использовано ≈" + used + " поисков");
            quotaDetailText.setText("Ориентировочный сброс через " + hours + " ч " + minutes + " мин. " +
                    "Текущая оценка ёмкости: ≈" + estimate + " треков на окно.");
        } else {
            int remaining = Math.max(0, estimate - used);
            quotaStatusText.setText("Использовано: " + used + " / ≈" + estimate + " • осталось ≈" + remaining);
            quotaDetailText.setText("Шкала оценочная: Spotify не публикует фиксированный лимит треков/день. " +
                    "Стартовый ориентир — ≈400 поисков; после QUOTA_EXCEEDED приложение запоминает фактическую оценку.");
        }
    }

'''
if needle not in s:
    raise SystemExit('spotifyRequest insertion point not found')
s=s.replace(needle,helpers+needle,1)

s=s.replace('''        } else if (quotaUntil != 0L) {\n            prefs.edit().remove("spotify_quota_until").apply();\n        }''','''        } else if (quotaUntil != 0L) {\n            prefs.edit().remove("spotify_quota_until").putInt("quota_track_searches_used", 0).putLong("quota_window_started_at", now).apply();\n            updateQuotaUi();\n        }''',1)

s=s.replace('''                runOnUiThread(() -> {\n                    getWindow().clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);\n                    progressArea.setVisibility(View.GONE);\n                    resultCard.setVisibility(View.VISIBLE);''','''                runOnUiThread(() -> {\n                    getWindow().clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);\n                    updateQuotaUi();\n                    progressArea.setVisibility(View.GONE);\n                    resultCard.setVisibility(View.VISIBLE);''',1)

bp=root/'app/build.gradle'
b=bp.read_text(encoding='utf-8')
b=b.replace('versionCode 11','versionCode 12').replace("versionName '1.1.0'","versionName '1.2.0'")
bp.write_text(b,encoding='utf-8')

p.write_text(s,encoding='utf-8')
print('Patched to v1.2.0 with quota meter')
