<?php
/**
 * Lumber Price Differential — PHP frontend
 * Calls main.py --json and renders the results as an HTML table.
 */

$zip1    = '';
$zip2    = '';
$results = null;
$error   = null;
$summary = null;

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $zip1    = preg_replace('/\D/', '', $_POST['zip1'] ?? '');
    $zip2    = preg_replace('/\D/', '', $_POST['zip2'] ?? '');
    $api_key = trim($_POST['api_key'] ?? getenv('SERPAPI_KEY') ?? '');

    if (strlen($zip1) !== 5 || strlen($zip2) !== 5) {
        $error = 'Both ZIP codes must be exactly 5 digits.';
    } elseif (empty($api_key)) {
        $error = 'An API key is required. Pass it below or set the SERPAPI_KEY environment variable.';
    } elseif (!preg_match('/^[\w\-]+$/', $api_key)) {
        $error = 'Invalid API key format.';
    } else {
        $script = __DIR__ . '/main.py';
        $cmd = sprintf(
            'python3 %s %s %s --key %s --json 2>/dev/null',
            escapeshellarg($script),
            escapeshellarg($zip1),
            escapeshellarg($zip2),
            escapeshellarg($api_key)
        );

        $raw = shell_exec($cmd);

        if (empty($raw)) {
            $error = 'No response from the price engine. Check your API key and try again.';
        } else {
            $data = json_decode($raw, true);
            if (!is_array($data)) {
                $error = 'Unexpected response format from price engine.';
            } else {
                $results = $data;

                // Compute summary stats
                $deltas  = array_filter(array_column($results, 'delta'), fn($d) => $d !== null);
                if (count($deltas)) {
                    $avg = array_sum($deltas) / count($deltas);
                    $summary = [
                        'avg'       => $avg,
                        'direction' => $avg > 0 ? "ZIP $zip2 is pricier" : ($avg < 0 ? "ZIP $zip2 is cheaper" : 'prices are equal'),
                    ];
                }
            }
        }
    }
}

function fmt_price(?float $v): string {
    return $v !== null ? '$' . number_format($v, 2) : 'N/A';
}

function fmt_delta(?float $d): string {
    if ($d === null) return 'N/A';
    $sign = $d >= 0 ? '+' : '';
    return $sign . '$' . number_format(abs($d), 2) . ($d < 0 ? '' : '');
}

function delta_class(?float $d): string {
    if ($d === null) return 'na';
    if ($d > 0)  return 'pos';
    if ($d < 0)  return 'neg';
    return 'zero';
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Lumber Price Differential</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    :root {
      --bg:      #1a1a1a;
      --panel:   #242424;
      --border:  #333333;
      --text:    #e0e0e0;
      --sub:     #9e9e9e;
      --amber:   #e8a020;
      --blue:    #4fc3f7;
      --red:     #ef5350;
      --green:   #66bb6a;
      --grey:    #90a4ae;
      --radius:  8px;
    }

    body {
      background: var(--bg);
      color: var(--text);
      font-family: 'Segoe UI', system-ui, sans-serif;
      min-height: 100vh;
      padding: 2rem 1rem;
    }

    .container {
      max-width: 860px;
      margin: 0 auto;
    }

    /* ── Header ── */
    header {
      text-align: center;
      margin-bottom: 2.5rem;
    }
    header h1 {
      font-size: 1.9rem;
      font-weight: 700;
      letter-spacing: .5px;
      color: var(--amber);
    }
    header p {
      color: var(--sub);
      margin-top: .4rem;
      font-size: .95rem;
    }

    /* ── Card ── */
    .card {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 1.75rem 2rem;
      margin-bottom: 1.5rem;
    }

    /* ── Form ── */
    .form-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1rem;
    }
    @media (max-width: 540px) {
      .form-grid { grid-template-columns: 1fr; }
    }
    .field {
      display: flex;
      flex-direction: column;
      gap: .35rem;
    }
    .field.full { grid-column: 1 / -1; }
    label {
      font-size: .8rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: .06em;
      color: var(--sub);
    }
    input[type="text"],
    input[type="password"] {
      background: var(--bg);
      border: 1px solid var(--border);
      border-radius: 5px;
      color: var(--text);
      font-size: 1rem;
      padding: .55rem .8rem;
      transition: border-color .15s;
      width: 100%;
    }
    input[type="text"]:focus,
    input[type="password"]:focus {
      outline: none;
      border-color: var(--amber);
    }
    input::placeholder { color: var(--sub); opacity: .6; }

    .btn {
      grid-column: 1 / -1;
      background: var(--amber);
      border: none;
      border-radius: 5px;
      color: #1a1a1a;
      cursor: pointer;
      font-size: 1rem;
      font-weight: 700;
      padding: .7rem 1.5rem;
      transition: opacity .15s;
      width: 100%;
      margin-top: .5rem;
    }
    .btn:hover { opacity: .85; }
    .btn:active { opacity: .7; }

    /* ── Error ── */
    .error {
      background: rgba(239,83,80,.12);
      border: 1px solid var(--red);
      border-radius: var(--radius);
      color: #ff8a80;
      padding: .9rem 1.2rem;
      margin-bottom: 1.5rem;
      font-size: .95rem;
    }

    /* ── Results ── */
    .results-header {
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      margin-bottom: 1rem;
      flex-wrap: wrap;
      gap: .5rem;
    }
    .results-header h2 {
      font-size: 1.1rem;
      font-weight: 600;
      color: var(--text);
    }
    .results-header .zips {
      font-size: .85rem;
      color: var(--sub);
    }
    .results-header .zips span {
      color: var(--amber);
      font-weight: 600;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      font-size: .9rem;
    }
    thead th {
      color: var(--sub);
      font-size: .75rem;
      font-weight: 600;
      letter-spacing: .07em;
      text-transform: uppercase;
      padding: .5rem .75rem;
      border-bottom: 1px solid var(--border);
      text-align: right;
    }
    thead th:first-child { text-align: left; }
    tbody tr:hover { background: rgba(255,255,255,.03); }
    tbody td {
      padding: .65rem .75rem;
      border-bottom: 1px solid var(--border);
      text-align: right;
    }
    tbody td:first-child { text-align: left; color: var(--text); }
    tbody td.na    { color: var(--grey); }
    tbody td.pos   { color: var(--red);   font-weight: 600; }
    tbody td.neg   { color: var(--green); font-weight: 600; }
    tbody td.zero  { color: var(--grey); }

    /* ── Summary bar ── */
    .summary {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-top: 1.2rem;
      padding: .75rem 1rem;
      background: rgba(255,255,255,.03);
      border-radius: 5px;
      border: 1px solid var(--border);
      flex-wrap: wrap;
      gap: .5rem;
    }
    .summary .label { color: var(--sub); font-size: .85rem; }
    .summary .value {
      font-size: 1.05rem;
      font-weight: 700;
    }
    .summary .value.pos { color: var(--red); }
    .summary .value.neg { color: var(--green); }
    .summary .value.zero { color: var(--grey); }
    .summary .direction { color: var(--sub); font-size: .85rem; }

    /* ── Footer ── */
    footer {
      text-align: center;
      color: var(--sub);
      font-size: .75rem;
      margin-top: 2.5rem;
    }
  </style>
</head>
<body>
<div class="container">

  <header>
    <h1>Lumber Price Differential</h1>
    <p>Compare Home Depot lumber prices between two ZIP codes</p>
  </header>

  <!-- Form -->
  <div class="card">
    <form method="POST" action="">
      <div class="form-grid">
        <div class="field">
          <label for="zip1">ZIP Code 1 <small>(baseline)</small></label>
          <input type="text" id="zip1" name="zip1"
                 value="<?= htmlspecialchars($zip1) ?>"
                 placeholder="e.g. 90210" maxlength="5" pattern="\d{5}" required>
        </div>
        <div class="field">
          <label for="zip2">ZIP Code 2 <small>(comparison)</small></label>
          <input type="text" id="zip2" name="zip2"
                 value="<?= htmlspecialchars($zip2) ?>"
                 placeholder="e.g. 10001" maxlength="5" pattern="\d{5}" required>
        </div>
        <div class="field full">
          <label for="api_key">SerpApi Key</label>
          <input type="password" id="api_key" name="api_key"
                 placeholder="Leave blank to use SERPAPI_KEY env var"
                 autocomplete="off">
        </div>
        <button type="submit" class="btn">Compare Prices</button>
      </div>
    </form>
  </div>

  <?php if ($error): ?>
  <div class="error"><?= htmlspecialchars($error) ?></div>
  <?php endif; ?>

  <?php if ($results !== null): ?>
  <div class="card">
    <div class="results-header">
      <h2>Results</h2>
      <div class="zips">
        <span><?= htmlspecialchars($zip1) ?></span>
        &nbsp;→&nbsp;
        <span><?= htmlspecialchars($zip2) ?></span>
      </div>
    </div>

    <table>
      <thead>
        <tr>
          <th>Product</th>
          <th>ZIP <?= htmlspecialchars($zip1) ?></th>
          <th>ZIP <?= htmlspecialchars($zip2) ?></th>
          <th>Delta</th>
        </tr>
      </thead>
      <tbody>
        <?php foreach ($results as $row): ?>
        <tr>
          <td><?= htmlspecialchars($row['query']) ?></td>
          <td class="<?= $row['zip1'] === null ? 'na' : '' ?>">
            <?= htmlspecialchars(fmt_price($row['zip1'])) ?>
          </td>
          <td class="<?= $row['zip2'] === null ? 'na' : '' ?>">
            <?= htmlspecialchars(fmt_price($row['zip2'])) ?>
          </td>
          <td class="<?= delta_class($row['delta']) ?>">
            <?= htmlspecialchars(fmt_delta($row['delta'])) ?>
          </td>
        </tr>
        <?php endforeach; ?>
      </tbody>
    </table>

    <?php if ($summary): ?>
    <div class="summary">
      <span class="label">Average delta per item</span>
      <div style="display:flex;align-items:baseline;gap:.6rem;">
        <span class="value <?= delta_class($summary['avg']) ?>">
          <?= htmlspecialchars(fmt_delta($summary['avg'])) ?>
        </span>
        <span class="direction">&mdash; <?= htmlspecialchars($summary['direction']) ?></span>
      </div>
    </div>
    <?php endif; ?>
  </div>
  <?php endif; ?>

  <footer>Data via SerpApi &middot; Home Depot &middot; Prices may vary</footer>

</div>
</body>
</html>
