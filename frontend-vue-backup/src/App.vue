<template>
  <div class="flex">
    <aside class="h-screen w-64 bg-slate-900 p-4 text-white">
      <div class="mb-6 text-lg font-semibold">DefiSys</div>
      <nav class="space-y-2">
        <RouterLink class="block rounded px-2 py-1 hover:bg-slate-800" to="/">
          Dashboard
        </RouterLink>
        <RouterLink class="block rounded px-2 py-1 hover:bg-slate-800" to="/logs">
          Logs
        </RouterLink>
        <RouterLink class="block rounded px-2 py-1 hover:bg-slate-800" to="/simulation">
          Simulação
      </RouterLink>
      </nav>
    </aside>

    <main class="h-screen flex-1 overflow-auto bg-slate-700 text-white">
      <router-view />
    </main>
  </div>
</template>
