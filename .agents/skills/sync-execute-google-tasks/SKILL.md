---
name: sync-execute-google-tasks
description: Sync and execute pending tasks from Google Tasks (list 'Principal') using AntigravityTasksManager. Triggered by /sync, "Vérifie mes tâches", or "Check mes to-do".
---

# Sync & Execute Google Tasks

## Déclenchement
Quand l'utilisateur tape `/sync` ou demande "Vérifie mes tâches" / "Check mes to-do".

## Procédure à exécuter
1. Importe `AntigravityTasksManager` depuis `Tools/tasks_manager.py`.
2. Appelle `get_pending_tasks()` sur la liste `Principal`.
3. S'il n'y a aucune tâche : réponds simplement "Aucune tâche en attente".
4. Si des tâches existent :
   - Pour chaque tâche, analyse le titre et le contenu des notes.
   - Applique les modifications de code ou le travail demandé dans le projet.
   - Clôture la tâche avec `mark_task_completed(task_id)`.
5. Affiche un résumé des actions effectuées à l'utilisateur.
