
mapboxgl.accessToken = 'put your key here';
var map = new mapboxgl.Map({
   container: 'map', // container id
   style: 'mapbox://styles/mapbox/streets-v11', // style URL
   center: [-74.5, 40], // starting position [lng, lat]
   zoom: 13 // starting zoom
});

let geoLocate = new mapboxgl.GeolocateControl({
   positionOptions: {
      enableHighAccuracy: true
   },
   trackUserLocation: true
})
map.addControl(
   geoLocate
)
let startingPoint

geoLocate.on('geolocate', (e) => {
   startingPoint = [e.coords.longitude, e.coords.latitude]

})

var geocoder = new MapboxGeocoder({
   accessToken: mapboxgl.accessToken,
   mapboxgl: mapboxgl,
   marker: false,
   placeholder: 'Cari lokasi tujuan'
});


document.getElementById('geocoder').appendChild(geocoder.onAdd(map));

let geojson = {
   "type": "FeatureCollection",
   "features": []
}

map.on('load', function () {
   map.addSource('custom', {
      type: 'geojson',
      data: geojson
   });

   map.addLayer({
      id: 'point',
      source: 'custom',
      type: 'circle',
      paint: {
         'circle-radius': 10,
         'circle-color': '#448ee4'
      }
   });

   geocoder.on('result', function (e) {
      let marker = {
         type: 'Feature',
         geometry: e.result.geometry
      }
      geojson.features.push(marker)
      map.getSource('custom').setData(geojson);
   });
});

function addLine(coordinates) {
   console.log(coordinates)
   map.addSource('route', {
      'type': 'geojson',
      'data': {
      'type': 'Feature',
      'properties': {},
      'geometry': {
      'type': 'LineString',
      'coordinates': coordinates
      }
      }
      });
      map.addLayer({
      'id': 'route',
      'type': 'line',
      'source': 'route',
      'layout': {
      'line-join': 'round',
      'line-cap': 'round'
      },
      'paint': {
      'line-color': '#888',
      'line-width': 5
      }
      });
}

const submitData = async () => {
   let locations = {};
   locations['L1'] = startingPoint
   geojson.features.forEach((marker, index) => {
      const key = `L${index + 2}`
      locations[key] = marker.geometry.coordinates
   });
   const url = 'http://localhost:5000/getroute'
   $.ajax({
      url: url,
      url: url,
      contentType: "application/json;charset=utf-8",
      dataType: "json",
      data: JSON.stringify({
         locations: locations
      }), success: function (data) {
         console.log("success")
         console.log(data)
         addLine(Object.values(data))
      },
      type: "POST",
   })
}
