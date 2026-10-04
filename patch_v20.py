from pathlib import Path
root=Path('VK2SpotifyAndroid')
p=root/'app/src/main/java/com/vk2spotify/transfer/MainActivity.java'
s=p.read_text(encoding='utf-8')

# New fields
s=s.replace('''    private EditText manualTracksInput;
    private TextView vkStatusText;''','''    private EditText manualTracksInput;
    private TextView vkStatusText;
    private TextView sourceWebTitle;
    private TextView vkDestinationStatusText;''',1)

s=s.replace('''    private Button spotifyButton;
    private Button transferButton;''','''    private Button spotifyButton;
    private Button openSourceButton;
    private Button transferButton;''',1)

s=s.replace('''    private LinearLayout spotifySetupArea;
    private LinearLayout manualArea;''','''    private LinearLayout spotifySetupArea;
    private LinearLayout spotifyControlsArea;
    private LinearLayout vkDestinationArea;
    private LinearLayout manualArea;''',1)

s=s.replace('''    private volatile Future<?> transferFuture;''','''    private volatile Future<?> transferFuture;
    private String selectedSource = "vk";
    private String destinationMode = "spotify";
    private final List<Track> vkDestinationQueue = new ArrayList<>();
    private int vkDestinationIndex;
    private int vkDestinationFound;
    private int vkDestinationMissing;''',1)

# Restore selected source before UI
s=s.replace('''        prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        setupPalette();
        buildUi();
        restoreVkTracks();''','''        prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        selectedSource = prefs.getString("selected_source", "vk");
        destinationMode = prefs.getString("destination_mode", "spotify");
        setupPalette();
        buildUi();
        restoreVkTracks();''',1)

# Header/stepper
s=s.replace('VK MUSIC  →  SPOTIFY   •   v1.2','MUSIC TRANSFER   •   v2.0',1)
s=s.replace('Вся музыка — в отдельный плейлист Spotify. Без ввода пароля Spotify в приложении.',
            'VK, Яндекс Музыка и Звук → Spotify или VK. Пароли сервисов вводятся только на их официальных страницах.',1)
s=s.replace('row.addView(stepChip("1", "VK", vkBlue), weightParams(1));',
            'row.addView(stepChip("1", "Источник", vkBlue), weightParams(1));',1)
s=s.replace('row.addView(stepChip("2", "Spotify", primary), weightParams(1));',
            'row.addView(stepChip("2", "Куда", primary), weightParams(1));',1)

# Replace source card
a=s.index('    private View sourceCard() {')
b=s.index('    private View spotifyCard() {',a)
source_method=r'''    private View sourceCard() {
        LinearLayout box = cardBox();
        box.addView(cardTop("Источник музыки", "VK / Яндекс / Звук", vkBlue));

        LinearLayout services = new LinearLayout(this);
        services.setOrientation(LinearLayout.HORIZONTAL);
        Button vk = smallButton("VK");
        Button ya = smallButton("Яндекс");
        Button zv = smallButton("Звук");
        vk.setOnClickListener(v -> selectSource("vk"));
        ya.setOnClickListener(v -> selectSource("yandex"));
        zv.setOnClickListener(v -> selectSource("zvuk"));
        services.addView(vk, weightParams(1));
        View g1=new View(this); services.addView(g1,new LinearLayout.LayoutParams(dp(6),1));
        services.addView(ya, weightParams(1));
        View g2=new View(this); services.addView(g2,new LinearLayout.LayoutParams(dp(6),1));
        services.addView(zv, weightParams(1));
        box.addView(services);

        vkStatusText = label("Источник: " + sourceName(selectedSource), 14, muted, Typeface.NORMAL);
        vkStatusText.setPadding(0, dp(9), 0, 0);
        box.addView(vkStatusText);

        trackCountText = label("0 треков", 28, text, Typeface.BOLD);
        trackCountText.setPadding(0, dp(4), 0, dp(12));
        box.addView(trackCountText);

        openSourceButton = actionButton("Открыть " + sourceName(selectedSource), sourceColor(selectedSource), Color.WHITE);
        openSourceButton.setOnClickListener(v -> openSource());
        box.addView(openSourceButton);

        Button manual = ghostButton("Не считалось? Вставить список вручную");
        manual.setOnClickListener(v -> {
            boolean show = manualArea.getVisibility() != View.VISIBLE;
            manualArea.setVisibility(show ? View.VISIBLE : View.GONE);
            manual.setText(show ? "Скрыть ручной импорт" : "Не считалось? Вставить список вручную");
        });
        box.addView(manual);

        manualArea = vertical();
        manualArea.setVisibility(View.GONE);
        manualArea.setPadding(0, dp(8), 0, 0);
        manualTracksInput = input("Исполнитель — Название\nИсполнитель — Название", true);
        manualTracksInput.setMinLines(5);
        manualTracksInput.setText(prefs.getString("manual_tracks", ""));
        manualTracksInput.addTextChangedListener(new SimpleWatcher() {
            @Override public void afterTextChanged(Editable e) {
                prefs.edit().putString("manual_tracks", e.toString()).apply();
                updateTrackCount();
                updateReadiness();
            }
        });
        manualArea.addView(manualTracksInput);
        TextView mh = label("По одному треку в строке. Подойдут —, –, - или табуляция.", 12, muted, Typeface.NORMAL);
        mh.setPadding(dp(3), dp(6), dp(3), 0);
        manualArea.addView(mh);
        box.addView(manualArea);
        return box;
    }

'''
s=s[:a]+source_method+s[b:]

# Replace spotify card with destination selector
a=s.index('    private View spotifyCard() {')
b=s.index('    private View quotaCard() {',a) if '    private View quotaCard() {' in s[a:] else s.index('    private View destinationCard() {',a)
spotify_method=r'''    private View spotifyCard() {
        LinearLayout box = cardBox();
        box.addView(cardTop("Куда переносим", "Spotify / VK", primary));

        LinearLayout destinations = new LinearLayout(this);
        destinations.setOrientation(LinearLayout.HORIZONTAL);
        Button sp = smallButton("Spotify");
        Button vk = smallButton("VK • эксперимент");
        sp.setOnClickListener(v -> selectDestination("spotify"));
        vk.setOnClickListener(v -> selectDestination("vk"));
        destinations.addView(sp, weightParams(1));
        View gap=new View(this); destinations.addView(gap,new LinearLayout.LayoutParams(dp(8),1));
        destinations.addView(vk, weightParams(1));
        box.addView(destinations);

        spotifyControlsArea = vertical();
        spotifyControlsArea.setPadding(0, dp(8), 0, 0);

        spotifyStatusText = label("Не подключён", 14, muted, Typeface.NORMAL);
        spotifyStatusText.setPadding(0, dp(7), 0, dp(12));
        spotifyControlsArea.addView(spotifyStatusText);

        spotifyButton = actionButton("Подключить Spotify", primary, Color.WHITE);
        spotifyButton.setOnClickListener(v -> startSpotifyLogin());
        spotifyControlsArea.addView(spotifyButton);

        Button setupToggle = ghostButton("Настройка Spotify API");
        setupToggle.setOnClickListener(v -> {
            boolean show = spotifySetupArea.getVisibility() != View.VISIBLE;
            spotifySetupArea.setVisibility(show ? View.VISIBLE : View.GONE);
            setupToggle.setText(show ? "Скрыть настройку" : "Настройка Spotify API");
        });
        spotifyControlsArea.addView(setupToggle);

        spotifySetupArea = vertical();
        spotifySetupArea.setVisibility(prefs.getString("spotify_client_id", "").isEmpty() ? View.VISIBLE : View.GONE);
        spotifySetupArea.setPadding(0, dp(8), 0, 0);

        clientIdInput = input("Spotify Client ID", false);
        clientIdInput.setText(prefs.getString("spotify_client_id", ""));
        spotifySetupArea.addView(clientIdInput);

        TextView explain = label("Client ID нужен один раз. Client Secret и пароль Spotify сюда вводить не нужно.", 12, muted, Typeface.NORMAL);
        explain.setPadding(dp(3), dp(4), dp(3), dp(8));
        spotifySetupArea.addView(explain);

        LinearLayout setupActions = new LinearLayout(this);
        setupActions.setOrientation(LinearLayout.HORIZONTAL);
        Button dashboard = smallButton("Открыть Dashboard");
        dashboard.setOnClickListener(v -> startActivity(new Intent(Intent.ACTION_VIEW,
                Uri.parse("https://developer.spotify.com/dashboard"))));
        setupActions.addView(dashboard, weightParams(1));
        View gap2 = new View(this);
        setupActions.addView(gap2, new LinearLayout.LayoutParams(dp(8), 1));
        Button copy = smallButton("Скопировать Redirect URI");
        copy.setOnClickListener(v -> {
            ClipboardManager cm = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
            cm.setPrimaryClip(ClipData.newPlainText("Spotify Redirect URI", REDIRECT_URI));
            toast("Redirect URI скопирован");
        });
        setupActions.addView(copy, weightParams(1));
        spotifySetupArea.addView(setupActions);

        TextView redirect = label(REDIRECT_URI, 12, muted, Typeface.NORMAL);
        redirect.setPadding(dp(3), dp(8), dp(3), 0);
        redirect.setTextIsSelectable(true);
        spotifySetupArea.addView(redirect);
        spotifyControlsArea.addView(spotifySetupArea);
        box.addView(spotifyControlsArea);

        vkDestinationArea = vertical();
        vkDestinationArea.setPadding(0, dp(10), 0, 0);
        vkDestinationStatusText = label("VK-назначение работает через официальный сайт: войди в VK, затем приложение будет искать и добавлять треки в «Мою музыку».", 13, muted, Typeface.NORMAL);
        vkDestinationStatusText.setLineSpacing(0,1.12f);
        vkDestinationArea.addView(vkDestinationStatusText);
        Button loginVk = actionButton("Открыть VK и войти", vkBlue, Color.WHITE);
        loginVk.setOnClickListener(v -> openVkDestinationLogin());
        vkDestinationArea.addView(loginVk);
        TextView exp = label("Экспериментально: интерфейс VK может меняться, поэтому часть треков может потребовать ручной проверки.", 12, muted, Typeface.NORMAL);
        exp.setPadding(0,dp(6),0,0);
        vkDestinationArea.addView(exp);
        box.addView(vkDestinationArea);

        selectDestination(destinationMode);
        return box;
    }

'''
s=s[:a]+spotify_method+s[b:]

# Overlay title and generic page finished
s=s.replace('TextView title = label("VK Музыка", 17, text, Typeface.BOLD);',
            'sourceWebTitle = label(sourceName(selectedSource), 17, text, Typeface.BOLD);',1)
s=s.replace('title.setGravity(Gravity.CENTER);','sourceWebTitle.setGravity(Gravity.CENTER);',1)\ns=s.replace('toolbar.addView(title, weightParams(1));','toolbar.addView(sourceWebTitle, weightParams(1));',1)
s=s.replace('collect.setOnClickListener(v -> startVkCollection());','collect.setOnClickListener(v -> startVkCollection());',1)
s=s.replace('''                if (url != null && (url.contains("vk.com") || url.contains("vk.ru"))) {
                    vkStatusText.setText("VK открыт — выбери музыку и нажми «Собрать»");
                }''','''                if (url != null) {
                    if (isAllowedSourceUrl(url, selectedSource)) {
                        vkStatusText.setText(sourceName(selectedSource) + " открыт — открой коллекцию/лайки и нажми «Собрать»");
                    } else if (url.contains("vk.com") || url.contains("vk.ru")) {
                        if (vkDestinationStatusText != null) vkDestinationStatusText.setText("VK открыт ✓ Можно вернуться и запускать перенос.");
                    }
                }''',1)

# Existing open/load methods -> generic
a=s.index('    private void openVk() {')
b=s.index('    private void startVkCollection() {',a)
generic_methods=r'''    private String sourceName(String source) {
        if ("yandex".equals(source)) return "Яндекс Музыка";
        if ("zvuk".equals(source)) return "Звук";
        return "VK Музыка";
    }

    private int sourceColor(String source) {
        if ("yandex".equals(source)) return Color.parseColor("#FFCC00");
        if ("zvuk".equals(source)) return Color.parseColor("#8B5CF6");
        return vkBlue;
    }

    private String sourceDefaultUrl(String source) {
        if ("yandex".equals(source)) return "https://music.yandex.ru/home";
        if ("zvuk".equals(source)) return "https://zvuk.com/";
        return "https://vk.com/audio";
    }

    private boolean isAllowedSourceUrl(String url, String source) {
        if (url == null) return false;
        if ("yandex".equals(source)) return url.contains("music.yandex.") || url.contains("yandex.ru/music");
        if ("zvuk".equals(source)) return url.contains("zvuk.com");
        return url.contains("vk.com") || url.contains("vk.ru");
    }

    private void selectSource(String source) {
        if (source == null || source.equals(selectedSource)) {
            updateSourceUi();
            return;
        }
        saveVkTracks();
        selectedSource = source;
        prefs.edit().putString("selected_source", selectedSource).apply();
        vkTracks.clear();
        loadTracksForSelectedSource();
        updateSourceUi();
        updateTrackCount();
        updateReadiness();
    }

    private void updateSourceUi() {
        if (openSourceButton != null) {
            openSourceButton.setText("Открыть " + sourceName(selectedSource));
            openSourceButton.setBackground(ripple(sourceColor(selectedSource), 15));
        }
        if (vkStatusText != null && vkTracks.isEmpty()) vkStatusText.setText("Источник: " + sourceName(selectedSource));
        if (sourceWebTitle != null) sourceWebTitle.setText(sourceName(selectedSource));
        if (vkUrlInput != null) vkUrlInput.setText(sourceDefaultUrl(selectedSource));
    }

    private void selectDestination(String mode) {
        destinationMode = "vk".equals(mode) ? "vk" : "spotify";
        if (prefs != null) prefs.edit().putString("destination_mode", destinationMode).apply();
        if (spotifyControlsArea != null) spotifyControlsArea.setVisibility("spotify".equals(destinationMode) ? View.VISIBLE : View.GONE);
        if (vkDestinationArea != null) vkDestinationArea.setVisibility("vk".equals(destinationMode) ? View.VISIBLE : View.GONE);
        if (playlistInput != null) playlistInput.setVisibility("spotify".equals(destinationMode) ? View.VISIBLE : View.GONE);
        updateReadiness();
    }

    private void openSource() {
        webOverlay.setVisibility(View.VISIBLE);
        getWindow().setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE);
        if (sourceWebTitle != null) sourceWebTitle.setText(sourceName(selectedSource));
        if (vkUrlInput != null) vkUrlInput.setText(sourceDefaultUrl(selectedSource));
        loadVkUrl();
    }

    private void openVk() { openSource(); }

    private void loadVkUrl() {
        String raw = vkUrlInput.getText().toString().trim();
        if (raw.isEmpty()) raw = sourceDefaultUrl(selectedSource);
        if (!isAllowedSourceUrl(raw, selectedSource) && !raw.startsWith("https://vk.com/") && !raw.startsWith("https://vk.ru/")) {
            toast("Открой ссылку выбранного музыкального сервиса");
            return;
        }
        vkWebView.loadUrl(raw);
        vkStatusText.setText("Открываю " + sourceName(selectedSource) + "…");
    }

    private void hideVkOverlay() {
        webOverlay.setVisibility(View.GONE);
    }

    private void openVkDestinationLogin() {
        webOverlay.setVisibility(View.VISIBLE);
        if (sourceWebTitle != null) sourceWebTitle.setText("VK — назначение");
        if (vkUrlInput != null) vkUrlInput.setText("https://vk.com/audio");
        vkWebView.loadUrl("https://vk.com/audio");
        if (vkDestinationStatusText != null) vkDestinationStatusText.setText("Войди в VK и открой раздел музыки. После этого вернись назад.");
    }

'''
s=s[:a]+generic_methods+s[b:]

# Generic source validation/status
s=s.replace('''        if (url == null || !(url.contains("vk.com") || url.contains("vk.ru"))) {
            toast("Сначала открой VK Музыку");
            return;
        }
        vkStatusText.setText("Готовлю страницу VK…");''','''        if (url == null || !isAllowedSourceUrl(url, selectedSource)) {
            toast("Сначала открой " + sourceName(selectedSource));
            return;
        }
        vkStatusText.setText("Готовлю " + sourceName(selectedSource) + "…");''',1)

# Extend parser selectors for Yandex and generic music services
s=s.replace("const sels=['.audio_row','[class*=\\\"audio_row\\\"]'",
            "const sels=['.d-track','[class*=\\\"d-track\\\"]','.audio_row','[class*=\\\"audio_row\\\"]'",1)
s=s.replace("let titleEl=r.querySelector('.audio_row__title_inner,.audio_row__title,",
            "let titleEl=r.querySelector('.d-track__name,.d-track__title,.audio_row__title_inner,.audio_row__title,",1)
s=s.replace("let artistEl=r.querySelector('.audio_row__performers,",
            "let artistEl=r.querySelector('.d-track__artists,.d-track__artist,.audio_row__performers,",1)

# Make saved tracks per source, while migrating old key
a=s.index('    private void saveVkTracks() {')
b=s.index('    private void startTransfer() {',a)
persist_methods=r'''    private String sourceTracksKey(String source) { return "source_tracks_" + source; }

    private void saveVkTracks() {
        JSONArray a=new JSONArray();
        for(Track t:vkTracks){ JSONObject o=new JSONObject(); try{o.put("artist",t.artist);o.put("title",t.title);a.put(o);}catch(Exception ignored){} }
        prefs.edit().putString(sourceTracksKey(selectedSource),a.toString()).apply();
    }

    private void loadTracksForSelectedSource() {
        try {
            String raw=prefs.getString(sourceTracksKey(selectedSource),"");
            if(raw.isEmpty() && "vk".equals(selectedSource)) raw=prefs.getString("vk_tracks_json","[]");
            JSONArray a=new JSONArray(raw.isEmpty()?"[]":raw);
            Set<String> seen=new HashSet<>(); List<Track> restored=new ArrayList<>();
            for(int i=0;i<a.length();i++){JSONObject o=a.optJSONObject(i);if(o==null)continue;String ar=o.optString("artist","").trim(), ti=o.optString("title","").trim();String k=normalize(ar)+"|"+normalize(ti);if(!ar.isEmpty()&&!ti.isEmpty()&&seen.add(k))restored.add(new Track(ar,ti));}
            vkTracks.clear(); vkTracks.addAll(restored);
            if(!restored.isEmpty() && vkStatusText!=null) vkStatusText.setText(sourceName(selectedSource)+": сохранено "+restored.size()+" "+trackWord(restored.size()));
        } catch(Exception ignored){}
    }

    private void restoreVkTracks() {
        loadTracksForSelectedSource();
        updateSourceUi();
        updateTrackCount();
        updateReadiness();
    }

    private void startTransfer() {
        if ("vk".equals(destinationMode)) startVkWebTransfer();
        else startSpotifyTransfer();
    }

'''
# Rename original transfer signature and prepend dispatcher
rest=s[b:]
rest=rest.replace('    private void startTransfer() {','    private void startSpotifyTransfer() {',1)
s=s[:a]+persist_methods+rest

# Update readiness method completely
a=s.index('    private void updateReadiness() {')
b=s.index('    private void updateTrackCount() {',a)
readiness=r'''    private void updateReadiness() {
        if (transferButton == null) return;
        int count = mergedTracks().size();
        boolean busy = progressArea != null && progressArea.getVisibility() == View.VISIBLE;
        if ("vk".equals(destinationMode)) {
            boolean ready = count > 0 && !busy;
            transferButton.setEnabled(ready);
            transferButton.setAlpha(ready ? 1f : 0.48f);
            transferButton.setText(ready ? "Добавить " + count + " " + trackWord(count) + " в VK" : "Сначала загрузите треки");
            return;
        }
        boolean spotifyReady = (spotifyAccessToken != null && !spotifyAccessToken.isEmpty()) || (spotifyRefreshToken != null && !spotifyRefreshToken.isEmpty());
        boolean ready = spotifyReady && count > 0 && !busy;
        transferButton.setEnabled(ready);
        transferButton.setAlpha(ready ? 1f : 0.48f);
        if (ready) transferButton.setText("Перенести " + count + " " + trackWord(count) + " в Spotify");
        else if (!spotifyReady && count == 0) transferButton.setText("Загрузите треки и подключите Spotify");
        else if (!spotifyReady) transferButton.setText("Сначала подключите Spotify");
        else transferButton.setText("Сначала загрузите треки");
    }

'''
s=s[:a]+readiness+s[b:]

# Generic source status in updateTrackCount
s=s.replace('if (count > 0 && vkTracks.isEmpty()) vkStatusText.setText("Ручной список готов");',
            'if (count > 0 && vkTracks.isEmpty()) vkStatusText.setText("Ручной список готов"); else if(count>0 && vkStatusText!=null) vkStatusText.setText(sourceName(selectedSource)+": собрано "+vkTracks.size()+" "+trackWord(vkTracks.size()));',1)

# Playlist default name should follow source
s=s.replace('playlistInput.setText("VK Music — " + new SimpleDateFormat("dd.MM.yyyy", Locale.getDefault()).format(new Date()));',
            'playlistInput.setText(sourceName(selectedSource) + " — " + new SimpleDateFormat("dd.MM.yyyy", Locale.getDefault()).format(new Date()));',1)

# Help text
s=s.replace('''1. Открой VK и войди в аккаунт.\n2. Нажми «Собрать треки».\n3. Подключи Spotify.\n4. Нажми перенос — приложение создаст отдельный приватный плейлист.''',
            '''1. Выбери VK, Яндекс Музыку или Звук и открой свою коллекцию.\n2. Нажми «Собрать».\n3. Выбери Spotify или VK как назначение.\n4. Для Spotify создаётся отдельный плейлист; для VK треки добавляются в «Мою музыку» через официальный сайт.''',1)

# Add VK destination transfer methods before updateReadiness
insert_at=s.index('    private void updateReadiness() {')
vk_methods=r'''    private void startVkWebTransfer() {
        List<Track> all=mergedTracks();
        if(all.isEmpty()){toast("Сначала загрузите треки");return;}
        String current=vkWebView==null?null:vkWebView.getUrl();
        if(current==null || !(current.contains("vk.com")||current.contains("vk.ru"))){
            toast("Сначала войди в VK через кнопку «Открыть VK и войти»");
            openVkDestinationLogin();
            return;
        }

        vkDestinationQueue.clear(); vkDestinationQueue.addAll(all);
        String hash=transferListHash(all);
        String oldHash=prefs.getString("vk_dest_hash","");
        vkDestinationIndex=hash.equals(oldHash)?Math.min(prefs.getInt("vk_dest_index",0),all.size()):0;
        vkDestinationFound=hash.equals(oldHash)?prefs.getInt("vk_dest_found",0):0;
        vkDestinationMissing=hash.equals(oldHash)?prefs.getInt("vk_dest_missing",0):0;
        prefs.edit().putString("vk_dest_hash",hash).apply();

        cancelRequested=false;
        resultCard.setVisibility(View.GONE);
        progressArea.setVisibility(View.VISIBLE);
        transferProgress.setProgress((int)Math.round(vkDestinationIndex*1000.0/all.size()));
        statsFoundText.setText("Добавлено  "+vkDestinationFound);
        statsMissingText.setText("Не найдено  "+vkDestinationMissing);
        transferStateText.setText("VK: начинаю с "+(vkDestinationIndex+1)+" из "+all.size()+"…");
        cancelButton.setEnabled(true); cancelButton.setText("Отменить перенос");
        processNextVkDestination();
    }

    private void processNextVkDestination() {
        if(cancelRequested){finishCancelledUi();return;}
        if(vkDestinationIndex>=vkDestinationQueue.size()){
            prefs.edit().remove("vk_dest_hash").remove("vk_dest_index").remove("vk_dest_found").remove("vk_dest_missing").apply();
            progressArea.setVisibility(View.GONE);
            resultCard.setVisibility(View.VISIBLE);
            resultText.setText("VK: готово. Добавлено/уже было: "+vkDestinationFound+" из "+vkDestinationQueue.size()+".\nНе найдено или интерфейс VK не распознан: "+vkDestinationMissing+".");
            openPlaylistButton.setEnabled(false);
            updateReadiness();
            return;
        }

        Track t=vkDestinationQueue.get(vkDestinationIndex);
        transferStateText.setText((vkDestinationIndex+1)+" / "+vkDestinationQueue.size()+"  •  "+t.artist+" — "+t.title);
        String q=Uri.encode(t.artist+" "+t.title);
        vkWebView.loadUrl("https://vk.com/audio?q="+q);
        handler.postDelayed(() -> tryVkDestinationTrack(t,0), 1900);
    }

    private void tryVkDestinationTrack(Track t,int attempt) {
        if(cancelRequested){finishCancelledUi();return;}
        String js=vkAddScript(t);
        vkWebView.evaluateJavascript(js,value->{
            String state="";
            try{Object d=new JSONTokener(value).nextValue();state=d instanceof String?(String)d:"";}catch(Exception ignored){}
            if(("added".equals(state)||"exists".equals(state))){
                vkDestinationFound++;
                finishVkDestinationItem();
            } else if(attempt<2) {
                handler.postDelayed(() -> tryVkDestinationTrack(t,attempt+1),900);
            } else {
                vkDestinationMissing++;
                finishVkDestinationItem();
            }
        });
    }

    private void finishVkDestinationItem() {
        vkDestinationIndex++;
        prefs.edit().putInt("vk_dest_index",vkDestinationIndex).putInt("vk_dest_found",vkDestinationFound).putInt("vk_dest_missing",vkDestinationMissing).commit();
        int progress=(int)Math.round(vkDestinationIndex*1000.0/Math.max(1,vkDestinationQueue.size()));
        transferProgress.setProgress(progress);
        statsFoundText.setText("Добавлено  "+vkDestinationFound);
        statsMissingText.setText("Не найдено  "+vkDestinationMissing);
        handler.postDelayed(this::processNextVkDestination,1050);
    }

    private String vkAddScript(Track t) {
        String a=JSONObject.quote(normalize(t.artist));
        String title=JSONObject.quote(normalize(t.title));
        return "(function(){"+
                "const norm=s=>(s||'').toLowerCase().replace(/ё/g,'е').replace(/[^a-zа-я0-9]+/gi,' ').trim();"+
                "const A="+a+",T="+title+";"+
                "const rows=[...document.querySelectorAll('.audio_row,[class*=\\\"audio_row\\\"],[class*=\\\"AudioRow\\\"],[data-testid*=\\\"audio\\\"]')];"+
                "let best=null,score=-1;for(const r of rows){let x=norm(r.innerText||r.textContent||'');let sc=0;if(T&&x.includes(T))sc+=2;if(A&&x.includes(A))sc+=2;if(sc>score){score=sc;best=r;}}"+
                "if(!best||score<2)return 'notfound';"+
                "const controls=[...best.querySelectorAll('button,[role=button],[aria-label],[title],a')];"+
                "for(const c of controls){let l=norm((c.getAttribute('aria-label')||'')+' '+(c.getAttribute('title')||'')+' '+(c.className||''));if(/удал.*мо|remove.*music|action_delete/.test(l))return 'exists';}"+
                "let add=best.querySelector('.audio_row__action_add,[class*=\\\"action_add\\\"],[aria-label*=\\\"Добав\\\"],[title*=\\\"Добав\\\"],[data-testid*=\\\"add\\\"],button[class*=\\\"add\\\"]');"+
                "if(add){add.click();return 'added';}return 'noadd';"+
                "})()";
    }

'''
s=s[:insert_at]+vk_methods+s[insert_at:]

# Version
bp=root/'app/build.gradle'
b=bp.read_text(encoding='utf-8')
b=b.replace('versionCode 12','versionCode 20').replace("versionName '1.2.0'","versionName '2.0.0'")
bp.write_text(b,encoding='utf-8')

p.write_text(s,encoding='utf-8')
print('Patched to v2.0 multisource')
