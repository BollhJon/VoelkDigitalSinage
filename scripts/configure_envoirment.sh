```bash
#!/bin/bash

echo "======================================"
echo " Signage Konfiguration"
echo "======================================"
echo

# Temporäre Liste für die Tournament IDs
IDS=()

echo "Tournament IDs eingeben"
echo "--------------------------------------"

while true; do
    read -p "Tournament ID: " ID

    # Leere Eingaben ignorieren
    if [ -z "$ID" ]; then
        echo "Keine ID eingegeben."
        continue
    fi

    IDS+=("$ID")

    read -p "Weitere ID hinzufügen? [j/n]: " MORE

    if [[ "$MORE" != "j" && "$MORE" != "J" ]]; then
        break
    fi
done

# IDs mit ; verbinden
TOURNAMENT_IDS=$(IFS=';'; echo "${IDS[*]}")

echo
echo "Start Mode"
echo "--------------------------------------"
echo "1) TURNIER"
echo "2) SPONSORING"
echo

while true; do
    read -p "Auswahl [1/2]: " MODE_CHOICE

    case "$MODE_CHOICE" in
        1)
            MODE="TURNIER"
            break
            ;;
        2)
            MODE="SPONSORING"
            break
            ;;
        *)
            echo "Ungültige Auswahl. Bitte 1 oder 2 eingeben."
            ;;
    esac
done

echo
echo "======================================"
echo " Folgende Konfiguration wird gesetzt:"
echo "======================================"
echo "SINAGE_TOURNAMENT_IDS=$TOURNAMENT_IDS"
echo "SINAGE_MODE=$MODE"
echo

read -p "Konfiguration speichern? [j/n]: " SAVE

if [[ "$SAVE" == "j" || "$SAVE" == "J" ]]; then

    # Bestehende Werte entfernen
    sudo sed -i '/^SINAGE_TOURNAMENT_IDS=/d' /etc/environment
    sudo sed -i '/^SINAGE_MODE=/d' /etc/environment

    # Neue Werte hinzufügen
    echo "SINAGE_TOURNAMENT_IDS=$TOURNAMENT_IDS" | sudo tee -a /etc/environment > /dev/null
    echo "SINAGE_MODE=$MODE" | sudo tee -a /etc/environment > /dev/null

    echo
    echo "Konfiguration wurde gespeichert."
    echo
    echo "Hinweis: Die neuen Umgebungsvariablen werden"
    echo "für neue Prozesse verfügbar. Eine bereits"
    echo "laufende Shell muss neu gestartet werden."
else
    echo
    echo "Konfiguration wurde NICHT gespeichert."
fi
```
