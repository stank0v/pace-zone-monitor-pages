// Draws the zones in #map-data on an OpenStreetMap base. Progressive: the
// page reads fully without it.
(function () {
  function start() {
    var el = document.getElementById('map'), data = document.getElementById('map-data');
    if (!el || !data || !window.L) return;
    var d = JSON.parse(data.textContent);
    var map = L.map(el, { scrollWheelZoom: false });
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 17, attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
    }).addTo(map);
    var group = L.featureGroup().addTo(map);
    d.zones.forEach(function (z) {
      var line = L.polyline(z.p, { color: '#137A47', weight: 6, opacity: 0.9 }).addTo(group);
      line.bindTooltip(z.n + ' · ' + z.l + ' km/h');
      if (z.u) line.on('click', function () { location.href = z.u; });
      if (d.ends) {
        L.circleMarker(z.p[0], { radius: 7, color: '#1B2430', fillColor: '#fff', fillOpacity: 1 }).addTo(group).bindTooltip('Начало');
        L.circleMarker(z.p[z.p.length - 1], { radius: 7, color: '#1B2430', fillColor: '#1B2430', fillOpacity: 1 }).addTo(group).bindTooltip('Край');
      }
    });
    map.fitBounds(group.getBounds(), { padding: [20, 20] });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
})();
