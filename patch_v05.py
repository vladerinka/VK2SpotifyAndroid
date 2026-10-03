from pathlib import Path

root = Path("VK2SpotifyAndroid")
p = root / "app/src/main/java/com/vk2spotify/transfer/MainActivity.java"
s = p.read_text(encoding="utf-8")

start = s.index("    private void startTransfer() {")
end = s.index("    private void updateReadiness() {")

new_block = r'''    private void startTransfer() {
        if (spotifyAccessToken == null || spotifyAccessToken.isEmpty()) {
            toast("Сначала подключи Spotify");
            return;
        }
        List<Track> all = mergedTracks();
        if (all.isEmpty()) {
            toast("Сначала загрузите треки");
            return;
        }

        String playlistName = playlistInput.getText().toString().trim();
        if (playlistName.isEmpty()) playlistName = "VK Music Import";
        final String finalPlaylistName = playlistName;
        final String listHash = transferListHash(all);

        String savedHash = prefs.getString("resume_hash", "");
        String savedPlaylistId = prefs.getString("resume_playlist_id", "");
        boolean canResume = listHash.equals(savedHash) && !savedPlaylistId.isEmpty();
        int savedIndex = canResume ? Math.min(prefs.getInt("resume_index", 0), all.size()) : 0;
        int savedFound = canResume ? prefs.getInt("resume_found", 0) : 0;
        int savedMissing = canResume ? prefs.getInt("resume_missing", 0) : 0;

        cancelRequested = false;
        resultCard.setVisibility(View.GONE);
        progressArea.setVisibility(View.VISIBLE);
        transferButton.setEnabled(false);
        transferButton.setAlpha(0.48f);
        cancelButton.setEnabled(true);
        cancelButton.setText("Отменить перенос");
        transferProgress.setProgress((int) Math.round(savedIndex * 1000.0 / all.size()));
        statsFoundText.setText("Найдено  " + savedFound);
        statsMissingText.setText("Не найдено  " + savedMissing);
        transferStateText.setText(canResume
                ? "Продолжаю с " + (savedIndex + 1) + " из " + all.size() + "…"
                : "Создаю плейлист и начинаю перенос " + all.size() + " треков…");

        executor.submit(() -> {
            try {
                String playlistId;
                String playlistUrl;
                int startIndex;
                int foundTotal;
                int missingTotal;
                List<String> pendingUris;

                if (canResume) {
                    playlistId = prefs.getString("resume_playlist_id", "");
                    playlistUrl = prefs.getString("resume_playlist_url", "");
                    startIndex = Math.min(prefs.getInt("resume_index", 0), all.size());
                    foundTotal = prefs.getInt("resume_found", 0);
                    missingTotal = prefs.getInt("resume_missing", 0);
                    pendingUris = loadPendingUris();
                    lastPlaylistUrl = playlistUrl.isEmpty() ? null : playlistUrl;

                    if (!pendingUris.isEmpty()) {
                        runOnUiThread(() -> transferStateText.setText(
                                "Добавляю сохранённый пакет в плейлист…"));
                        addItemsToPlaylist(playlistId, pendingUris);
                        pendingUris.clear();
                        saveResumeState(listHash, playlistId, playlistUrl, startIndex,
                                foundTotal, missingTotal, pendingUris);
                    }
                } else {
                    clearResumeState();
                    PlaylistResult playlist = createSpotifyPlaylist(finalPlaylistName);
                    playlistId = playlist.id;
                    playlistUrl = playlist.url == null ? "" : playlist.url;
                    lastPlaylistUrl = playlist.url;
                    startIndex = 0;
                    foundTotal = 0;
                    missingTotal = 0;
                    pendingUris = new ArrayList<>();
                    saveResumeState(listHash, playlistId, playlistUrl, 0, 0, 0, pendingUris);
                }

                List<Track> notFoundExamples = new ArrayList<>();
                for (int i = startIndex; i < all.size(); i++) {
                    if (cancelRequested) throw new TransferCancelled();

                    Track t = all.get(i);
                    String uri = findSpotifyTrack(t);
                    if (uri != null) {
                        foundTotal++;
                        pendingUris.add(uri);
                    } else {
                        missingTotal++;
                        if (notFoundExamples.size() < 12) notFoundExamples.add(t);
                    }

                    int done = i + 1;
                    saveResumeState(listHash, playlistId, playlistUrl, done,
                            foundTotal, missingTotal, pendingUris);

                    if (pendingUris.size() >= 50) {
                        runOnUiThread(() -> transferStateText.setText(
                                "Сохраняю найденные треки в плейлист…"));
                        addItemsToPlaylist(playlistId, pendingUris);
                        pendingUris.clear();
                        saveResumeState(listHash, playlistId, playlistUrl, done,
                                foundTotal, missingTotal, pendingUris);
                    }

                    int finalFound = foundTotal;
                    int finalMissing = missingTotal;
                    int progress = (int) Math.round(done * 1000.0 / all.size());
                    runOnUiThread(() -> {
                        transferProgress.setProgress(progress);
                        transferStateText.setText(done + " / " + all.size() + "  •  "
                                + t.artist + " — " + t.title);
                        statsFoundText.setText("Найдено  " + finalFound);
                        statsMissingText.setText("Не найдено  " + finalMissing);
                    });

                    Thread.sleep(1150);
                }

                if (!pendingUris.isEmpty()) {
                    runOnUiThread(() -> transferStateText.setText(
                            "Добавляю последние найденные треки…"));
                    addItemsToPlaylist(playlistId, pendingUris);
                    pendingUris.clear();
                }

                lastPlaylistUrl = playlistUrl.isEmpty() ? null : playlistUrl;
                clearResumeState();

                StringBuilder summary = new StringBuilder();
                summary.append("Готово. Найдено и перенесено ")
                        .append(foundTotal).append(" из ").append(all.size()).append(" треков.");
                summary.append("\nНе найдено: ").append(missingTotal).append(".");
                if (!notFoundExamples.isEmpty()) {
                    summary.append("\n\nПримеры ненайденных:\n");
                    for (Track t : notFoundExamples) {
                        summary.append("• ").append(t.artist).append(" — ")
                                .append(t.title).append("\n");
                    }
                }

                String finalSummary = summary.toString();
                runOnUiThread(() -> {
                    getWindow().clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
                    progressArea.setVisibility(View.GONE);
                    resultCard.setVisibility(View.VISIBLE);
                    resultText.setText(finalSummary);
                    openPlaylistButton.setEnabled(lastPlaylistUrl != null);
                    updateReadiness();
                });

            } catch (SpotifyQuotaExceeded e) {
                int done = prefs.getInt("resume_index", 0);
                int found = prefs.getInt("resume_found", 0);
                int missing = prefs.getInt("resume_missing", 0);
                String url = prefs.getString("resume_playlist_url", "");
                lastPlaylistUrl = url.isEmpty() ? null : url;
                int hours = Math.max(1, (int) Math.ceil(e.retryAfterSeconds / 3600.0));

                runOnUiThread(() -> {
                    getWindow().clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
                    progressArea.setVisibility(View.GONE);
                    resultCard.setVisibility(View.VISIBLE);
                    resultText.setText("Spotify исчерпал квоту Development Mode.\n\n" +
                            "Обработано: " + done + " из " + all.size() + "\n" +
                            "Найдено: " + found + " • не найдено: " + missing + "\n\n" +
                            "Попробуй примерно через " + hours + " ч. " +
                            "Снова собери тот же список треков, подключи Spotify и нажми перенос — " +
                            "приложение продолжит автоматически с сохранённого места.");
                    openPlaylistButton.setEnabled(lastPlaylistUrl != null);
                    updateReadiness();
                });

            } catch (TransferCancelled e) {
                runOnUiThread(() -> {
                    getWindow().clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
                    progressArea.setVisibility(View.GONE);
                    toast("Перенос остановлен. Прогресс сохранён.");
                    updateReadiness();
                });

            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                runOnUiThread(() -> {
                    getWindow().clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
                    progressArea.setVisibility(View.GONE);
                    updateReadiness();
                });

            } catch (Exception e) {
                runOnUiThread(() -> {
                    getWindow().clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
                    progressArea.setVisibility(View.GONE);
                    resultCard.setVisibility(View.VISIBLE);
                    resultText.setText("Перенос остановлен: " + e.getMessage() +
                            "\n\nЕсли плейлист уже был создан, прогресс сохранён и следующая попытка продолжит его.");
                    openPlaylistButton.setEnabled(lastPlaylistUrl != null);
                    updateReadiness();
                });
            }
        });

        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
    }

    private String transferListHash(List<Track> tracks) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            for (Track t : tracks) {
                String line = normalize(t.artist) + "|" + normalize(t.title) + "\n";
                md.update(line.getBytes(StandardCharsets.UTF_8));
            }
            return Base64.encodeToString(md.digest(), Base64.NO_WRAP);
        } catch (Exception e) {
            return "fallback-" + tracks.size();
        }
    }

    private void saveResumeState(String hash, String playlistId, String playlistUrl,
                                 int index, int found, int missing, List<String> pending) {
        JSONArray arr = new JSONArray();
        for (String uri : pending) arr.put(uri);
        prefs.edit()
                .putString("resume_hash", hash)
                .putString("resume_playlist_id", playlistId)
                .putString("resume_playlist_url", playlistUrl == null ? "" : playlistUrl)
                .putInt("resume_index", index)
                .putInt("resume_found", found)
                .putInt("resume_missing", missing)
                .putString("resume_pending", arr.toString())
                .apply();
    }

    private List<String> loadPendingUris() {
        List<String> out = new ArrayList<>();
        String raw = prefs.getString("resume_pending", "[]");
        try {
            JSONArray arr = new JSONArray(raw);
            for (int i = 0; i < arr.length(); i++) {
                String uri = arr.optString(i, "");
                if (!uri.isEmpty()) out.add(uri);
            }
        } catch (Exception ignored) { }
        return out;
    }

    private void clearResumeState() {
        prefs.edit()
                .remove("resume_hash")
                .remove("resume_playlist_id")
                .remove("resume_playlist_url")
                .remove("resume_index")
                .remove("resume_found")
                .remove("resume_missing")
                .remove("resume_pending")
                .apply();
    }

'''

s = s[:start] + new_block + s[end:]
p.write_text(s, encoding="utf-8")

bp = root / "app/build.gradle"
b = bp.read_text(encoding="utf-8")
b = b.replace("versionCode 4", "versionCode 5").replace("versionName '0.4.0'", "versionName '0.5.0'")
bp.write_text(b, encoding="utf-8")
print("Patched to v0.5.0")
