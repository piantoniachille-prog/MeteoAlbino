<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Meteo & Ambiente Albino (Val Seriana)</title>
    <!-- Google Fonts -->
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #0b1329;
            --card-bg: rgba(255, 255, 255, 0.04);
            --card-border: rgba(255, 255, 255, 0.08);
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --accent-blue: #38bdf8;
            --accent-glow: rgba(56, 189, 248, 0.15);
        }

        body {
            font-family: 'Inter', sans-serif;
            background-color: var(--bg-color);
            background-image: 
                radial-gradient(circle at 10% 20%, rgba(14, 165, 233, 0.12) 0%, transparent 40%),
                radial-gradient(circle at 90% 80%, rgba(99, 102, 241, 0.08) 0%, transparent 40%);
            color: var(--text-main);
            margin: 0;
            padding: 20px;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }

        .dashboard {
            width: 100%;
            max-width: 700px;
            background: var(--card-bg);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            padding: 35px;
            border-radius: 24px;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
            border: 1px solid var(--card-border);
        }

        h1 {
            font-size: 1.6rem;
            margin-bottom: 5px;
            color: var(--text-main);
            font-weight: 700;
        }

        h1 span {
            color: var(--accent-blue);
        }

        .subtitle {
            font-size: 0.9rem;
            color: var(--text-muted);
            margin-bottom: 30px;
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 16px;
            margin-bottom: 20px;
        }

        .card {
            background: rgba(255, 255, 255, 0.02);
            padding: 20px;
            border-radius: 16px;
            border: 1px solid var(--card-border);
            transition: all 0.3s ease;
        }

        .card:hover {
            transform: translateY(-2px);
            border-color: rgba(56, 189, 248, 0.3);
            box-shadow: 0 10px 30px -10px var(--accent-glow);
        }

        .card-title {
            font-size: 0.75rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.1em;
            margin-bottom: 8px;
            font-weight: 600;
        }

        .card-value {
            font-size: 1.8rem;
            font-weight: 700;
            color: var(--text-main);
        }

        .alert-card {
            background: rgba(255, 255, 255, 0.02);
            padding: 20px;
            border-radius: 16px;
            border: 1px solid var(--card-border);
            grid-column: span 2;
        }

        .status-ok {
            color: #34d399;
            font-weight: 600;
        }

        .status-critico {
            color: #f87171;
            font-weight: 600;
        }

        .footer {
            margin-top: 30px;
            text-align: center;
            font-size: 0.8rem;
            color: var(--text-muted);
            border-top: 1px solid var(--card-border);
            padding-top: 20px;
        }
    </style>
</head>
<body>

    <div class="dashboard">
        <h1>Albino (BG) • <span>Stazione Meteo</span></h1>
        <div class="subtitle">Monitoraggio microclimatico e ambientale in Val Seriana</div>

        <div class="grid">
            <div class="card">
                <div class="card-title">Temperatura</div>
                <div class="card-value" id="temp">-- °C</div>
            </div>
            <div class="card">
                <div class="card-title">Umidità Relativa</div>
                <div class="card-value" id="humidity">-- %</div>
            </div>
            <div class="card">
                <div class="card-title">Pressione (SLM)</div>
                <div class="card-value" id="pressure">-- hPa</div>
            </div>
            <div class="card">
                <div class="card-title">Vento</div>
                <div class="card-value" id="wind">-- km/h</div>
            </div>
            <div class="card" style="grid-column: span 2;">
                <div class="card-title">Precipitazioni (Giornaliere)</div>
                <div class="card-value" id="daily">-- mm</div>
            </div>
            <div class="alert-card">
                <div class="card-title">Qualità dell'Aria / Analisi Ambientale</div>
                <div class="card-value" id="air-quality" style="font-size: 1.05rem; margin-top: 5px;">Caricamento dati in corso...</div>
            </div>
        </div>

        <div class="footer" id="timestamp">Ultimo aggiornamento: In attesa...</div>
    </div>

    <script>
        async function caricaDatiMeteo() {
            try {
                const response = await fetch('ultimo_stato.json?t=' + new Date().getTime());
                if (!response.ok) throw new Error('File dati non trovato');
                
                const data = await response.json();

                document.getElementById('temp').innerText = data.temperatura_c + " °C";
                document.getElementById('humidity').innerText = data.umidita_pct + " %";
                document.getElementById('pressure').innerText = data.pressione_hpa + " hPa";
                document.getElementById('wind').innerText = data.vento_kmh + " km/h";
                document.getElementById('rain').innerText = (data.pioggia_mm !== undefined ? data.pioggia_mm : 0.0) + " mm";
                
                const airElement = document.getElementById('air-quality');
                airElement.innerText = data.qualita_aria_stimata;
                
                if(data.qualita_aria_stimata.includes("CRITICO")) {
                    airElement.className = "status-critico";
                } else {
                    airElement.className = "status-ok";
                }

                document.getElementById('timestamp').innerText = "Ultimo aggiornamento da Ecowitt: " + data.timestamp;

            } catch (error) {
                console.error("Errore nel caricamento:", error);
                document.getElementById('air-quality').innerText = "Impossibile leggere il file dei dati.";
            }
        }

        caricaDatiMeteo();
    </script>

</body>
</html>
