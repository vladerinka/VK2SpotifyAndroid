from pathlib import Path

root = Path("VK2SpotifyAndroid")
p = root / "app/src/main/java/com/vk2spotify/transfer/MainActivity.java"
s = p.read_text(encoding="utf-8")

old = r'''    private String findSpotifyTrack(Track target) throws Exception {
        String query = "track:\"" + target.title + "\" artist:\"" + target.artist + "\"";
        Uri uri = Uri.parse("https://api.spotify.com/v1/search").buildUpon()
                .appendQueryParameter("q", query)
                .appendQueryParameter("type", "track")
                .appendQueryParameter("limit", "5")
                .build();
        HttpResult res = spotifyRequest("GET", uri.toString(), null);
        if (res.code == 401) throw new Exception("Spotify-сессия закончилась. Подключи Spotify заново.");
        if (res.code < 200 || res.code >= 300) return null;

        JSONObject root = new JSONObject(res.body);
        JSONArray items = root.optJSONObject("tracks") != null
                ? root.getJSONObject("tracks").optJSONArray("items") : null;
        if (items == null || items.length() == 0) return fallbackTitleSearch(target);

        Candidate best = bestCandidate(target, items);
        if (best != null && best.score >= 0.58) return best.uri;
        return fallbackTitleSearch(target);
    }

    private String fallbackTitleSearch(Track target) throws Exception {
        Uri uri = Uri.parse("https://api.spotify.com/v1/search").buildUpon()
                .appendQueryParameter("q", target.artist + " " + target.title)
                .appendQueryParameter("type", "track")
                .appendQueryParameter("limit", "5")
                .build();
        HttpResult res = spotifyRequest("GET", uri.toString(), null);
        if (res.code < 200 || res.code >= 300) return null;
        JSONObject root = new JSONObject(res.body);
        JSONObject tracks = root.optJSONObject("tracks");
        JSONArray items = tracks == null ? null : tracks.optJSONArray("items");
        Candidate best = bestCandidate(target, items);
        return best != null && best.score >= 0.62 ? best.uri : null;
    }
'''
new = r'''    private String findSpotifyTrack(Track target) throws Exception {
        Uri uri = Uri.parse("https://api.spotify.com/v1/search").buildUpon()
                .appendQueryParameter("q", target.artist + " " + target.title)
                .appendQueryParameter("type", "track")
                .appendQueryParameter("limit", "10")
                .build();
        HttpResult res = spotifyRequest("GET", uri.toString(), null);
        if (res.code == 401) throw new Exception("Spotify-сессия закончилась. Подключи Spotify заново.");
        if (res.code < 200 || res.code >= 300) return null;

        JSONObject root = new JSONObject(res.body);
        JSONObject tracks = root.optJSONObject("tracks");
        JSONArray items = tracks == null ? null : tracks.optJSONArray("items");
        Candidate best = bestCandidate(target, items);
        return best != null && best.score >= 0.58 ? best.uri : null;
    }
'''
if old not in s:
    raise SystemExit("search block not found")
s = s.replace(old, new, 1)

old = r'''    private HttpResult spotifyRequest(String method, String url, String body) throws Exception {
        HttpResult last = null;
        for (int attempt = 0; attempt < 5; attempt++) {
            if (cancelRequested) throw new TransferCancelled();
            last = http(method, url, spotifyAccessToken, "application/json", body);
            if (last.code != 429) return last;
            int wait = Math.max(2, last.retryAfterSeconds);
            int finalWait = wait;
            runOnUiThread(() -> transferStateText.setText("Spotify просит паузу — " + finalWait + " сек…"));
            Thread.sleep(wait * 1000L);
        }
        return last;
    }
'''
new = r'''    private HttpResult spotifyRequest(String method, String url, String body) throws Exception {
        HttpResult last = null;
        for (int attempt = 0; attempt < 5; attempt++) {
            if (cancelRequested) throw new TransferCancelled();
            last = http(method, url, spotifyAccessToken, "application/json", body);
            if (last.code != 429) return last;

            int wait = Math.max(2, last.retryAfterSeconds);
            String reason = "";
            try {
                JSONObject error = new JSONObject(last.body);
                reason = error.optString("reason", "");
                if (reason.isEmpty() && error.optJSONObject("error") != null) {
                    reason = error.optJSONObject("error").optString("reason", "");
                }
            } catch (Exception ignored) { }

            if ("QUOTA_EXCEEDED".equalsIgnoreCase(reason) || wait > 300) {
                throw new SpotifyQuotaExceeded(wait);
            }

            int finalWait = wait;
            runOnUiThread(() -> transferStateText.setText(
                    "Spotify ограничил частоту запросов — пауза " + finalWait + " сек…"));
            Thread.sleep(wait * 1000L);
        }
        return last;
    }
'''
if old not in s:
    raise SystemExit("request block not found")
s = s.replace(old, new, 1)

s = s.replace("Thread.sleep(280);", "Thread.sleep(1150);", 1)

needle = r'''            } catch (InterruptedException e) {
'''
insert = r'''            } catch (SpotifyQuotaExceeded e) {
                int hours = Math.max(1, (int) Math.ceil(e.retryAfterSeconds / 3600.0));
                runOnUiThread(() -> {
                    getWindow().clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
                    progressArea.setVisibility(View.GONE);
                    resultCard.setVisibility(View.VISIBLE);
                    resultText.setText("Spotify исчерпал квоту Development Mode.\n" +
                            "Повтори перенос примерно через " + hours + " ч.\n\n" +
                            "Процесс остановлен сразу — приложение больше не будет висеть сутками на таймере.");
                    openPlaylistButton.setEnabled(false);
                    updateReadiness();
                });
'''
if needle not in s:
    raise SystemExit("catch marker not found")
s = s.replace(needle, insert + needle, 1)

needle = r'''    private static class TransferCancelled extends Exception { }
'''
repl = r'''    private static class TransferCancelled extends Exception { }

    private static class SpotifyQuotaExceeded extends Exception {
        final int retryAfterSeconds;
        SpotifyQuotaExceeded(int retryAfterSeconds) { this.retryAfterSeconds = retryAfterSeconds; }
    }
'''
if needle not in s:
    raise SystemExit("exception marker not found")
s = s.replace(needle, repl, 1)

p.write_text(s, encoding="utf-8")

bp = root / "app/build.gradle"
b = bp.read_text(encoding="utf-8")
b = b.replace("versionCode 3", "versionCode 4").replace("versionName '0.3.0'", "versionName '0.4.0'")
bp.write_text(b, encoding="utf-8")
print("Patched to v0.4.0")
