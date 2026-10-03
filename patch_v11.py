from pathlib import Path
root=Path('VK2SpotifyAndroid')
p=root/'app/src/main/java/com/vk2spotify/transfer/MainActivity.java'
s=p.read_text(encoding='utf-8')

# imports / fields
s=s.replace('import java.util.concurrent.Executors;\n', 'import java.util.concurrent.Executors;\nimport java.util.concurrent.Future;\n', 1)
s=s.replace('    private String lastPlaylistUrl;\n    private volatile boolean cancelRequested;\n',
'''    private String lastPlaylistUrl;\n    private volatile boolean cancelRequested;\n    private volatile HttpURLConnection activeConnection;\n    private volatile Future<?> transferFuture;\n''',1)

# visible version label so user can verify installed build
s=s.replace('TextView eyebrow = label("VK MUSIC  →  SPOTIFY", 12, muted, Typeface.BOLD);',
            'TextView eyebrow = label("VK MUSIC  →  SPOTIFY   •   v1.1", 12, muted, Typeface.BOLD);',1)

# cancellation button: immediate UI + interrupt background work + disconnect active request
old='''        cancelButton.setOnClickListener(v -> {\n            cancelRequested = true;\n            cancelButton.setEnabled(false);\n            cancelButton.setText("Отменяем…");\n        });'''
new='''        cancelButton.setOnClickListener(v -> requestTransferCancel());'''
if old not in s:
    raise SystemExit('cancel button block not found')
s=s.replace(old,new,1)

# safer destroy
old='''    protected void onDestroy() {\n        super.onDestroy();\n        cancelRequested = true;\n        executor.shutdownNow();\n        if (vkWebView != null) vkWebView.destroy();\n    }'''
new='''    protected void onDestroy() {\n        cancelRequested = true;\n        HttpURLConnection c = activeConnection;\n        if (c != null) c.disconnect();\n        Future<?> f = transferFuture;\n        if (f != null) f.cancel(true);\n        executor.shutdownNow();\n        if (vkWebView != null) vkWebView.destroy();\n        super.onDestroy();\n    }'''
if old not in s:
    raise SystemExit('onDestroy block not found')
s=s.replace(old,new,1)

# quota preflight
needle='''        final String finalPlaylistName = playlistName;\n        final String listHash = transferListHash(all);\n\n        String savedHash = prefs.getString("resume_hash", "");'''
repl='''        final String finalPlaylistName = playlistName;\n        final String listHash = transferListHash(all);\n\n        long quotaUntil = prefs.getLong("spotify_quota_until", 0L);\n        long now = System.currentTimeMillis();\n        if (quotaUntil > now) {\n            long seconds = Math.max(1L, (quotaUntil - now + 999L) / 1000L);\n            long hours = Math.max(1L, (seconds + 3599L) / 3600L);\n            resultCard.setVisibility(View.VISIBLE);\n            resultText.setText("Spotify временно исчерпал квоту Development Mode.\\n\\n" +\n                    "Ориентировочно осталось: " + hours + " ч.\\n" +\n                    "Прогресс сохранён — после сброса квоты перенос продолжится с места остановки.");\n            progressArea.setVisibility(View.GONE);\n                        updateReadiness();\n            return;\n        } else if (quotaUntil != 0L) {\n            prefs.edit().remove("spotify_quota_until").apply();\n        }\n\n        String savedHash = prefs.getString("resume_hash", "");'''
if needle not in s:
    raise SystemExit('quota preflight insertion point not found')
s=s.replace(needle,repl,1)

# hold Future
old='''        executor.submit(() -> {'''
new='''        transferFuture = executor.submit(() -> {'''
idx=s.index('    private void startTransfer() {')
pos=s.index(old,idx)
s=s[:pos]+s[pos:].replace(old,new,1)

s=s.replace('                    Thread.sleep(1150);','                    sleepCancellable(1150L);',1)
s=s.replace('            Thread.sleep(wait * 1000L);','            sleepCancellable(wait * 1000L);',1)

cs=s.index('            } catch (TransferCancelled e) {', s.index('    private void startTransfer() {'))
ce=s.index('\n        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);', cs)
new_catches=r'''            } catch (TransferCancelled e) {
                runOnUiThread(this::finishCancelledUi);

            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                runOnUiThread(this::finishCancelledUi);

            } catch (Exception e) {
                if (cancelRequested) {
                    runOnUiThread(this::finishCancelledUi);
                } else {
                    runOnUiThread(() -> {
                        getWindow().clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
                        progressArea.setVisibility(View.GONE);
                        resultCard.setVisibility(View.VISIBLE);
                        resultText.setText("Перенос остановлен: " + e.getMessage() +
                                "\\n\\nЕсли плейлист уже был создан, прогресс сохранён и следующая попытка продолжит его.");
                        openPlaylistButton.setEnabled(lastPlaylistUrl != null);
                        updateReadiness();
                    });
                }
            } finally {
                transferFuture = null;
            }
        });
'''
s=s[:cs]+new_catches+s[ce:]

needle='''    private String transferListHash(List<Track> tracks) {'''
helpers='''    private void requestTransferCancel() {\n        if (cancelRequested) return;\n        cancelRequested = true;\n        if (cancelButton != null) {\n            cancelButton.setEnabled(false);\n            cancelButton.setText("Остановлено ✓");\n        }\n\n        HttpURLConnection c = activeConnection;\n        if (c != null) c.disconnect();\n        Future<?> f = transferFuture;\n        if (f != null) f.cancel(true);\n\n        finishCancelledUi();\n    }\n\n    private void finishCancelledUi() {\n        getWindow().clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);\n        if (progressArea != null) progressArea.setVisibility(View.GONE);\n        if (cancelButton != null) {\n            cancelButton.setEnabled(true);\n            cancelButton.setText("Отменить перенос");\n        }\n        if (resultCard != null && resultText != null) {\n            resultCard.setVisibility(View.VISIBLE);\n            resultText.setText("Перенос остановлен. Прогресс сохранён.\\n\\n" +\n                    "При следующем запуске с тем же списком треков приложение продолжит с места остановки.");\n            if (openPlaylistButton != null) openPlaylistButton.setEnabled(lastPlaylistUrl != null);\n        }\n                updateReadiness();\n    }\n\n    private void sleepCancellable(long millis) throws InterruptedException, TransferCancelled {\n        long end = System.currentTimeMillis() + Math.max(0L, millis);\n        while (true) {\n            if (cancelRequested) throw new TransferCancelled();\n            long left = end - System.currentTimeMillis();\n            if (left <= 0L) return;\n            Thread.sleep(Math.min(250L, left));\n        }\n    }\n\n'''
if needle not in s:
    raise SystemExit('helper insertion point not found')
s=s.replace(needle,helpers+needle,1)

old='''    private HttpResult http(String method, String urlText, String bearer, String contentType, String body) throws Exception {\n        HttpURLConnection c = (HttpURLConnection) new URL(urlText).openConnection();\n        c.setConnectTimeout(20000);\n        c.setReadTimeout(30000);\n        c.setRequestMethod(method);\n        c.setRequestProperty("Accept", "application/json");\n        if (bearer != null) c.setRequestProperty("Authorization", "Bearer " + bearer);\n        if (body != null) {\n            c.setDoOutput(true);\n            c.setRequestProperty("Content-Type", contentType);\n            byte[] bytes = body.getBytes(StandardCharsets.UTF_8);\n            c.setFixedLengthStreamingMode(bytes.length);\n            try (OutputStream os = c.getOutputStream()) { os.write(bytes); }\n        }\n        int code = c.getResponseCode();\n        String retry = c.getHeaderField("Retry-After");\n        int retrySeconds = 0;\n        try { retrySeconds = retry == null ? 0 : Integer.parseInt(retry.trim()); } catch (Exception ignored) { }\n        InputStream stream = code >= 200 && code < 400 ? c.getInputStream() : c.getErrorStream();\n        String response = readAll(stream);\n        c.disconnect();\n        return new HttpResult(code, response, retrySeconds);\n    }'''
new='''    private HttpResult http(String method, String urlText, String bearer, String contentType, String body) throws Exception {\n        HttpURLConnection c = (HttpURLConnection) new URL(urlText).openConnection();\n        activeConnection = c;\n        try {\n            c.setConnectTimeout(20000);\n            c.setReadTimeout(30000);\n            c.setRequestMethod(method);\n            c.setRequestProperty("Accept", "application/json");\n            if (bearer != null) c.setRequestProperty("Authorization", "Bearer " + bearer);\n            if (body != null) {\n                c.setDoOutput(true);\n                c.setRequestProperty("Content-Type", contentType);\n                byte[] bytes = body.getBytes(StandardCharsets.UTF_8);\n                c.setFixedLengthStreamingMode(bytes.length);\n                try (OutputStream os = c.getOutputStream()) { os.write(bytes); }\n            }\n            int code = c.getResponseCode();\n            String retry = c.getHeaderField("Retry-After");\n            int retrySeconds = 0;\n            try { retrySeconds = retry == null ? 0 : Integer.parseInt(retry.trim()); } catch (Exception ignored) { }\n            InputStream stream = code >= 200 && code < 400 ? c.getInputStream() : c.getErrorStream();\n            String response = readAll(stream);\n            return new HttpResult(code, response, retrySeconds);\n        } finally {\n            if (activeConnection == c) activeConnection = null;\n            c.disconnect();\n        }\n    }'''
if old not in s:
    raise SystemExit('http block not found')
s=s.replace(old,new,1)

s=s.replace('            if (last.code != 429) return last;',
'''            if (last.code != 429) {\n                prefs.edit().remove("spotify_quota_until").apply();\n                return last;\n            }''',1)

bp=root/'app/build.gradle'
b=bp.read_text(encoding='utf-8')
b=b.replace('versionCode 10','versionCode 11').replace("versionName '1.0.0'","versionName '1.1.0'")
bp.write_text(b,encoding='utf-8')

p.write_text(s,encoding='utf-8')
print('Patched to v1.1.0')
