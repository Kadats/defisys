import { createRouter, createWebHistory } from "vue-router";
import DashboardView from "../views/DashboardView.vue";
import LogsView from "../views/LogsView.vue";

const routes = [
  { path: "/", name: "Dashboard", component: DashboardView },
  { path: "/logs", name: "Logs", component: LogsView },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
