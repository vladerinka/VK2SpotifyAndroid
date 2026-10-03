from pathlib import Path
root=Path('VK2SpotifyAndroid')
p=root/'app/src/main/java/com/vk2spotify/transfer/MainActivity.java'
s=p.read_text()

s=s.replace('    private String spotifyAccessToken;\n    private String lastPlaylistUrl;\n', '    private String spotifyAccessToken;\n    private String spotifyRefreshToken;\n    private long spotifyTokenExpiresAt;\n    private String lastPlaylistUrl;\n',1)
s=s.replace('        buildUi();\n        handleAuthIntent(getIntent());\n','        buildUi();\n        restoreVkTracks();\n        restoreSpotifySession();\n        handleAuthIntent(getIntent());\n',1)

# persist manual input
s=s.replace('        manualTracksInput = input("Исполнитель — Название\\nИсполнитель — Название", true);\n        manualTracksInput.setMinLines(5);\n','        manualTracksInput = input("Исполнитель — Название\\nИсполнитель — Название", true);\n        manualTracksInput.setMinLines(5);\n        manualTracksInput.setText(prefs.getString("manual_tracks", ""));\n',1)
s=s.replace('            @Override public void afterTextChanged(Editable s) {\n                updateTrackCount();','            @Override public void afterTextChanged(Editable s) {\n                prefs.edit().putString("manual_tracks", s.toString()).apply();\n                updateTrackCount();',1)

# save VK list after successful parse
needle='''                if (!parsed.isEmpty()) {\n                    vkTracks.clear();\n                    vkTracks.addAll(parsed);\n                    saveVkTracks();\n                }\n'''
if needle not in s:
    old='''                if (!parsed.isEmpty()) {\n                    vkTracks.clear();\n                    vkTracks.addAll(parsed);\n                }\n'''
    if old in s: s=s.replace(old, old.replace('                }\n','                    saveVkTracks();\n                }\n',1),1)

# replace auth block up to startTransfer
st=s.index('    private void exchangeSpotifyToken(String code) {')
en=s.index('    private void startTransfer() {')
new=r'''    private void exchangeSpotifyToken(String code) {
        String clientId = prefs.getString("spotify_client_id", "");
        String verifier = prefs.getString("pkce_verifier", "");
        if (clientId.isEmpty() || verifier.isEmpty()) { spotifyStatusText.setText("Подключись ещё раз"); return; }
        spotifyStatusText.setText("Подключаю Spotify…");
        executor.submit(() -> {
            try {
                String body=formEncode("client_id",clientId,"grant_type","authorization_code","code",code,"redirect_uri",REDIRECT_URI,"code_verifier",verifier);
                HttpResult res=http("POST","https://accounts.spotify.com/api/token",null,"application/x-www-form-urlencoded",body);
                if(res.code<200||res.code>=300) throw new Exception("HTTP "+res.code+": "+shortBody(res.body));
                saveSpotifyTokens(new JSONObject(res.body), true);
                prefs.edit().remove("pkce_verifier").remove("oauth_state").apply();
                runOnUiThread(() -> spotifyConnectedUi());
            } catch(Exception e) { runOnUiThread(() -> spotifyStatusText.setText("Не удалось подключить: "+e.getMessage())); }
        });
    }

    private void saveSpotifyTokens(JSONObject j, boolean needRefresh) throws Exception {
        String access=j.optString("access_token","");
        String refresh=j.optString("refresh_token", spotifyRefreshToken==null?"":spotifyRefreshToken);
        if(access.isEmpty() || (needRefresh&&refresh.isEmpty())) throw new Exception("Spotify не вернул токен");
        spotifyAccessToken=access; spotifyRefreshToken=refresh;
        spotifyTokenExpiresAt=System.currentTimeMillis()+Math.max(60,j.optInt("expires_in",3600))*1000L;
        prefs.edit().putString("spotify_access_token",access).putString("spotify_refresh_token",refresh).putLong("spotify_token_expiry",spotifyTokenExpiresAt).commit();
    }

    private void restoreSpotifySession() {
        spotifyAccessToken=prefs.getString("spotify_access_token","");
        spotifyRefreshToken=prefs.getString("spotify_refresh_token","");
        spotifyTokenExpiresAt=prefs.getLong("spotify_token_expiry",0L);
        if(!spotifyAccessToken.isEmpty() && System.currentTimeMillis()<spotifyTokenExpiresAt-60000L){ spotifyConnectedUi(); return; }
        if(!spotifyRefreshToken.isEmpty() && !prefs.getString("spotify_client_id","").isEmpty()) {
            spotifyStatusText.setText("Восстанавливаю Spotify…");
            executor.submit(() -> { try { refreshSpotifyToken(); runOnUiThread(this::spotifyConnectedUi); }
                catch(Exception e){ runOnUiThread(() -> spotifyStatusText.setText("Нужно подключить Spotify заново")); } });
        }
    }

    private void spotifyConnectedUi() {
        spotifyStatusText.setText("Подключён ✓"); spotifyButton.setText("Spotify подключён ✓"); spotifyButton.setAlpha(0.76f);
        spotifySetupArea.setVisibility(View.GONE); updateReadiness();
    }

    private void refreshSpotifyToken() throws Exception {
        String clientId=prefs.getString("spotify_client_id","");
        if(spotifyRefreshToken==null||spotifyRefreshToken.isEmpty()) spotifyRefreshToken=prefs.getString("spotify_refresh_token","");
        if(clientId.isEmpty()||spotifyRefreshToken.isEmpty()) throw new Exception("Нет refresh token");
        String body=formEncode("client_id",clientId,"grant_type","refresh_token","refresh_token",spotifyRefreshToken);
        HttpResult res=http("POST","https://accounts.spotify.com/api/token",null,"application/x-www-form-urlencoded",body);
        if(res.code<200||res.code>=300) throw new Exception("HTTP "+res.code);
        saveSpotifyTokens(new JSONObject(res.body), false);
    }

    private void ensureSpotifyToken() throws Exception {
        if(spotifyAccessToken!=null&&!spotifyAccessToken.isEmpty()&&System.currentTimeMillis()<spotifyTokenExpiresAt-60000L) return;
        refreshSpotifyToken();
    }

    private void saveVkTracks() {
        JSONArray a=new JSONArray();
        for(Track t:vkTracks){ JSONObject o=new JSONObject(); try{o.put("artist",t.artist);o.put("title",t.title);a.put(o);}catch(Exception ignored){} }
        prefs.edit().putString("vk_tracks_json",a.toString()).apply();
    }

    private void restoreVkTracks() {
        try {
            JSONArray a=new JSONArray(prefs.getString("vk_tracks_json","[]"));
            Set<String> seen=new HashSet<>(); List<Track> restored=new ArrayList<>();
            for(int i=0;i<a.length();i++){JSONObject o=a.optJSONObject(i);if(o==null)continue;String ar=o.optString("artist","").trim(), ti=o.optString("title","").trim();String k=normalize(ar)+"|"+normalize(ti);if(!ar.isEmpty()&&!ti.isEmpty()&&seen.add(k))restored.add(new Track(ar,ti));}
            if(!restored.isEmpty()){vkTracks.clear();vkTracks.addAll(restored);vkStatusText.setText("Восстановлен сохранённый список");updateTrackCount();updateReadiness();}
        } catch(Exception ignored){}
    }

'''
s=s[:st]+new+s[en:]

# spotifyRequest auto-refresh
st=s.index('    private HttpResult spotifyRequest(String method, String url, String body) throws Exception {')
en=s.index('    private HttpResult http(String method, String urlText, String bearer, String contentType, String body) throws Exception {')
req=r'''    private HttpResult spotifyRequest(String method, String url, String body) throws Exception {
        HttpResult last=null; boolean refreshed=false;
        for(int attempt=0;attempt<6;attempt++){
            if(cancelRequested) throw new TransferCancelled();
            ensureSpotifyToken();
            last=http(method,url,spotifyAccessToken,"application/json",body);
            if(last.code==401&&!refreshed){refreshSpotifyToken();refreshed=true;continue;}
            if(last.code!=429)return last;
            int wait=Math.max(2,last.retryAfterSeconds); String reason="";
            try{JSONObject e=new JSONObject(last.body);reason=e.optString("reason","");if(reason.isEmpty()&&e.optJSONObject("error")!=null)reason=e.optJSONObject("error").optString("reason","");}catch(Exception ignored){}
            if("QUOTA_EXCEEDED".equalsIgnoreCase(reason)||wait>300)throw new SpotifyQuotaExceeded(wait);
            int w=wait;runOnUiThread(() -> transferStateText.setText("Spotify ограничил частоту запросов — пауза "+w+" сек…"));Thread.sleep(wait*1000L);
        }
        return last;
    }

'''
s=s[:st]+req+s[en:]

# refresh-aware readiness and transfer gate
s=s.replace('        if (spotifyAccessToken == null || spotifyAccessToken.isEmpty()) {','        if ((spotifyAccessToken == null || spotifyAccessToken.isEmpty()) && (spotifyRefreshToken == null || spotifyRefreshToken.isEmpty())) {',1)
s=s.replace('        boolean spotifyReady = spotifyAccessToken != null && !spotifyAccessToken.isEmpty();','        boolean spotifyReady = (spotifyAccessToken != null && !spotifyAccessToken.isEmpty()) || (spotifyRefreshToken != null && !spotifyRefreshToken.isEmpty());',1)

# durable resume state
s=s.replace('.putString("resume_pending", arr.toString())\n                .apply();','.putString("resume_pending", arr.toString())\n                .commit();',1)

p.write_text(s)

bp=root/'app/build.gradle';b=bp.read_text().replace('versionCode 5','versionCode 10').replace("versionName '0.5.0'","versionName '1.0.0'");bp.write_text(b)
mp=root/'app/src/main/AndroidManifest.xml';mp.write_text(mp.read_text().replace('android:allowBackup="true"','android:allowBackup="false"'))
print('ok')
