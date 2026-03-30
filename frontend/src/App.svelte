<script>
  import Router from 'svelte-spa-router';
  import Layout from './components/Layout.svelte';
  import Dashboard from './pages/Dashboard.svelte';
  import Detections from './pages/Detections.svelte';
  import Species from './pages/Species.svelte';
  import SpeciesDetail from './pages/SpeciesDetail.svelte';
  import History from './pages/History.svelte';
  import WeeklyReport from './pages/WeeklyReport.svelte';
  import Recordings from './pages/Recordings.svelte';
  import Livestream from './pages/Livestream.svelte';
  import Settings from './pages/Settings.svelte';

  const routes = {
    '/': Dashboard,
    '/detections': Detections,
    '/species': Species,
    '/species/:sciName': SpeciesDetail,
    '/history': History,
    '/weekly': WeeklyReport,
    '/recordings': Recordings,
    '/livestream': Livestream,
    '/settings': Settings,
  };
</script>

<Layout>
  <Router {routes} />
</Layout>
