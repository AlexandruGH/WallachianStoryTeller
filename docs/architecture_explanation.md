# Arhitectura Sistemului de Narațiune (Cache & Graph)

## 1. Cum se generează Hash-ul din Graf?

Hash-ul nu este un simplu ID al nodului din graf. El reprezintă o **amprentă digitală unică a întregii stări a jocului** în acel moment.

Procesul de generare (în `graph_story_builder.py`):

1.  **Simulare (BFS):** Scriptul parcurge graful pas cu pas, simulând un jucător care alege fiecare opțiune.
2.  **Construirea Contextului:** Pentru fiecare pas, scriptul construiește un `prompt` complet, identic cu cel trimis la LLM (AI). Acest prompt include:
    *   Istoricul dialogului (ultimele replici).
    *   Statistici caracter (Viață, Aur, Reputație).
    *   Inventar.
    *   Instrucțiuni de sistem.
3.  **Hashing:** Se aplică algoritmul `SHA-512` pe acest text complet (`prompt`).
    *   `hash = SHA512(prompt)`
4.  **Mapare:** Hash-ul rezultat este cheia în fișierul compilat (`strajer_draculesti.json`).
    *   `"a3f19..." : { "narrative": "...", ... }`

## 2. Rolul Fișierului Sursă (`_source.json`)

Fișierul sursă (ex: `strajer_source.json`) are un rol dublu și critic:

### A. Planul Arhitectural (Blueprint)
Este versiunea **lizibilă de către om**. Aici definim logica narativă.

### B. Sistemul de Siguranță (Offline Fallback)
Aici intervine partea esențială:

**De ce nu putem renunța la Sursă și să folosim doar Hash-uri?**

Răspunsul este **Explozia Combinatorială**.

Hash-ul depinde de *starea exactă*.
*   Dacă jucătorul are **100 HP**, hash-ul este `X`.
*   Dacă jucătorul are **99 HP** (a pierdut 1 HP într-un eveniment random anterior), hash-ul este `Y`.
*   Dacă jucătorul a ajuns aici pe ruta A vs ruta B, istoricul e diferit => hash `Z`.

Pentru a acoperi *toate* posibilitățile exclusiv prin hash-uri, ar trebui să pre-generăm milioane de fișiere pentru fiecare combinație posibilă de Viață, Aur, Inventar și Istoric. Este imposibil.

**Soluția Hibridă:**
1.  **Hash Cache (Compilat):** Acoperă "Calea Ideală" (Golden Path) și cele mai comune variații. Este foarte rapid și sigur.
2.  **Source Cache (Fallback):** Acoperă **orice altă situație**. Dacă jucătorul are o stare neprevăzută (ex: 98 HP în loc de 100), hash-ul nu se potrivește, dar jocul caută textul acțiunii ("Atacă") în Sursă și găsește răspunsul corect.

Fără fișierul sursă, orice mică deviere de la scenariul pre-calculat ar duce la o eroare (cum ați observat anterior).
