// function to handle the synchronization of data
async function synchData(){

    try {
        const response = await fetch('/api/sync', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        document.getElementById('results').innerHTML = `<p>${data.message}</p>`;
    } catch (error) {
        document.getElementById('results').innerHTML = `<p>Erreur: ${error}</p>`;
    }
}

// function to handle the generation of data
async function generateData() {
    const count = document.getElementById('count').value;
    try {
        const response = await fetch('/api/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ count: parseInt(count) })
        });
        const data = await response.json();
        document.getElementById('results').innerHTML = `<p>${data.message}</p>`;
    } catch (error) {
        document.getElementById('results').innerHTML = `<p>Error: ${error}</p>`;
    }
}

// function to handle the searching of data
async function searchText() {
    const query = document.getElementById('searchText').value;
    if (query.length < 3) {
        document.getElementById('results').innerHTML = '';
        return;
    }
    try {
        const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
        const data = await response.json();
        document.getElementById('results').innerHTML = data.results
            .map(r => `<p><strong>${r.firstname} ${r.lastname}</strong>, ${r.city} (${r.country}) - ${r.email}</p>`)
            .join('');
    } catch (error) {
        document.getElementById('results').innerHTML = `<p>Error: ${error}</p>`;
    }
}

// function to handle the searching of data by geo
async function searchGeo() {
    const lat = document.getElementById('lat').value;
    const lon = document.getElementById('lon').value;
    const radius = document.getElementById('radius').value;
    try {
        const response = await fetch(`/api/search?lat=${lat}&lon=${lon}&radius=${radius}`);
        const data = await response.json();
        document.getElementById('results').innerHTML = data.results
            .map(r => `<p><strong>${r.firstname} ${r.lastname}</strong>, ${r.city} (${r.location.lat}, ${r.location.lon})</p>`)
            .join('');
    } catch (error) {
        document.getElementById('results').innerHTML = `<p>Error: ${error}</p>`;
    }
}