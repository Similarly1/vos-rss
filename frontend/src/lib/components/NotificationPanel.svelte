<script>
    import { createEventDispatcher } from 'svelte';
    import { fly, fade } from 'svelte/transition';
    
    export let isOpen = false;
    export let notifications = [
        { id: 1, title: 'Rafraîchissement terminé', message: '12 nouveaux articles ont été récupérés.', type: 'info', read: false, time: 'Il y a 5 min' },
        { id: 2, title: 'Article Majeur', message: 'L\'IA a détecté un article très pertinent sur SvelteKit.', type: 'highlight', read: false, time: 'Il y a 1h' }
    ];

    const dispatch = createEventDispatcher();

    function markAllAsRead() {
        notifications = notifications.map(n => ({ ...n, read: true }));
    }

    function handleNotificationClick(notif) {
        const index = notifications.findIndex(n => n.id === notif.id);
        if (index !== -1) notifications[index].read = true;
        notifications = [...notifications];
        
        dispatch('navigate', notif);
        isOpen = false;
    }
</script>

{#if isOpen}
    <!-- Overlay invisible pour fermer le panel au clic en dehors -->
    <div class="fixed inset-0 z-40" on:click={() => isOpen = false} transition:fade={{duration: 150}}></div>

    <div class="absolute right-0 top-12 mt-2 w-80 z-50 bg-slate-900 border border-slate-700/80 rounded-2xl shadow-2xl overflow-hidden origin-top-right"
         transition:fly="{{ y: -10, duration: 200 }}">
        
        <div class="p-4 border-b border-slate-800 flex justify-between items-center bg-slate-900/50 backdrop-blur-md">
            <h3 class="font-semibold text-white">Notifications</h3>
            {#if notifications.some(n => !n.read)}
                <button on:click={markAllAsRead} class="text-xs text-blue-400 hover:text-blue-300 transition-colors">
                    Tout marquer comme lu
                </button>
            {/if}
        </div>

        <div class="max-h-96 overflow-y-auto">
            {#if notifications.length === 0}
                <div class="p-6 text-center text-slate-500 text-sm">
                    Aucune notification.
                </div>
            {:else}
                {#each notifications as notif (notif.id)}
                    <button 
                        class="w-full text-left p-4 border-b border-slate-800/50 hover:bg-slate-800 transition-colors flex gap-3 relative {notif.read ? 'opacity-70' : ''}"
                        on:click={() => handleNotificationClick(notif)}
                    >
                        {#if !notif.read}
                            <div class="absolute left-0 top-0 bottom-0 w-1 bg-blue-500"></div>
                        {/if}
                        
                        <div class="flex-shrink-0 mt-1">
                            {#if notif.type === 'info'}
                                <div class="w-8 h-8 rounded-full bg-blue-500/20 text-blue-400 flex items-center justify-center">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                                </div>
                            {:else}
                                <div class="w-8 h-8 rounded-full bg-amber-500/20 text-amber-400 flex items-center justify-center">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"></path></svg>
                                </div>
                            {/if}
                        </div>
                        
                        <div>
                            <h4 class="text-sm font-medium text-slate-200 {notif.read ? '' : 'text-white'}">{notif.title}</h4>
                            <p class="text-xs text-slate-400 mt-1 leading-relaxed">{notif.message}</p>
                            <span class="text-[10px] text-slate-500 mt-2 block">{notif.time}</span>
                        </div>
                    </button>
                {/each}
            {/if}
        </div>
    </div>
{/if}
