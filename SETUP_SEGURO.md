# ⚙️ Configuração Segura para Jogos Competitivos

## 🔒 Passo 1: Configurar Chaves de API (SEGURANÇA CRÍTICA)

### Criar arquivo .env
```powershell
Copy-Item .env.example .env
```

### Editar .env
Abra o `.env` e adicione sua chave do Groq:
```
GROQ_API_KEY=sua_chave_aqui
```

**⚠️ NUNCA commitar o arquivo .env!** Ele está protegido pelo .gitignore.

## 🎮 Passo 2: Configurar para Jogos com Anti-Cheat

### Criar config.json seguro
```powershell
Copy-Item config.safe.example.json config.json
```

Ou edite seu `config.json` com estas configurações:

```json
{
  "push_to_talk_key": "caps_lock",
  "preferred_provider": "groq",
  "groq_api_key": "",
  "gemini_api_key": "",
  "voice": "pt-BR-ThalitaMultilingualNeural",
  "voice_rate": "+5%",
  "voice_pitch": "+0Hz",
  "play_chimes": true,
  "chime_volume": 0.2,
  "game_profile": "universal",
  "enable_screen_vision": true,
  "sentinel_mode_enabled": true,
  "sentinel_interval_seconds": 25,
  "anti_cheat_protection": true,
  "input_method": "windows_hotkey"
}
```

### Configurações Importantes:
- **`anti_cheat_protection": true`** - Ativa modo stealth automático
- **`input_method": "windows_hotkey"`** - Usa Windows API (mais seguro)
- **`groq_api_key": ""`** - Deixe vazio, a chave vem do .env

## 🎯 Passo 3: Escolher Tecla de Atalho

### Para Windows Hotkey (mais seguro):
Teclas suportadas:
- `caps_lock`, `scroll_lock`, `num_lock`
- `f1`, `f2`, `f3`, `f4`, `f5`, `f6`, `f7`, `f8`, `f9`, `f10`, `f11`, `f12`
- `0`, `1`, `2`, `3`, `4`, `5`, `6`, `7`, `8`, `9`
- `a`, `b`, `c`, `d`, `e`, `f`, `g`, `h`, `i`, `j`, `k`, `l`, `m`, `n`, `o`, `p`, `q`, `r`, `s`, `t`, `u`, `v`, `w`, `x`, `y`, `z`

**Recomendado:** `caps_lock` ou `f1` (fácil de alcançar durante jogo)

### Para Pynput (padrão, mais flexível):
Teclas suportadas:
- Todas as do Windows Hotkey
- Modificadores: `alt_l`, `alt_r`, `ctrl_l`, `ctrl_r`, `shift_l`, `shift_r`
- Mouse: `xbutton1`, `xbutton2` (botões laterais)

**⚠️ Pynput pode ser detectado por anti-cheats rigorosos!**

## 🚀 Passo 4: Iniciar o Sidekick

```powershell
python run_sidekick.py
```

Você verá:
```
🎮  SIDEKICK — SEU COPILOTO GAMER UNIVERSAL
============================================================
-> Tecla Push-to-Talk: [CAPS_LOCK]
-> Voz: pt-BR-ThalitaMultilingualNeural
-> Modo Sentinela (Auto-Vigiar): ATIVADO (intervalo: 25s)
-> Proteção Anti-Cheat: ATIVADO
-> Método de Input: Windows Hotkey (Mais Seguro)
-> Ícone de Gamepad adicionado à bandeja do Windows (System Tray).
============================================================
```

## 📊 Status do Ícone no Tray

- **Verde/Ciano:** Modo normal (jogo seguro)
- **Laranja/Vermelho com triângulo:** Modo stealth ativo (anti-cheat detectado)

## 🎮 Jogos e Configurações Recomendadas

### Jogos Single-Player (Seguros):
- Dark Souls, Elden Ring, Cyberpunk, Baldur's Gate 3
- **Config:** Pode usar `input_method": "pynput"` e visão ativada

### Jogos Online com Anti-Cheat:
- Valorant, LoL, CS2, Albion Online, PoE, GTA V
- **Config:** Use `input_method": "windows_hotkey"` + `anti_cheat_protection": true`

### Jogos Online Leves:
- Minecraft, Rocket League, Warframe
- **Config:** Pode usar pynput, mas cuidado em servidores competitivos

## ⚠️ Avisos Importantes

1. **Sempre use .env para chaves de API** - Nunca coloque chaves reais no config.json
2. **Windows Hotkey é mais seguro** - Mas menos flexível (sem mouse, sem modificadores)
3. **Modo Stealth desativa visão** - Em jogos com anti-cheat, você só terá áudio
4. **Use por sua conta e risco** - Não há garantia 100% contra ban
5. **Teste em jogos não-competitivos primeiro** - Valide o funcionamento antes de usar em ranked

## 🔧 Solução de Problemas

### Windows Hotkey não funciona:
- Verifique se a tecla está na lista de suportadas
- Tente outra tecla (ex: `f1` ao invés de `caps_lock`)
- Use `"input_method": "pynput"` como fallback

### Ícone não muda para stealth:
- Verifique se `"anti_cheat_protection": true` no config
- Abra um jogo com anti-cheat e verifique o console

### Chave de API não funciona:
- Verifique se o arquivo `.env` existe
- Confirme que a chave está correta no `.env`
- O config.json deve ter `"groq_api_key": ""` (vazio)
