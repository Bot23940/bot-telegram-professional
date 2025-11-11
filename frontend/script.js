async function loadStats(){
  try {
    const r = await fetch('/products');
    const data = await r.json();
    const s = document.getElementById('stats');
    s.innerHTML = '<h3>Produits</h3>' + data.products.map(p => `<div class="prod"><b>${p.filename}</b> - Prix: ${p.price}€ - Stock: ${p.available}</div>`).join('');
  } catch(e) {
    document.getElementById('stats').innerText = 'Erreur: ' + e;
  }
}
loadStats();
