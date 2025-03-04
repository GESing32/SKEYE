# ground_app.py (Skeleton for Ground Application)
import json
import folium  # For mapping
import paho.mqtt.client as mqtt  # For receiving data

class GroundApplication:
    def __init__(self):
        self.data = []
        self.mqtt_client = self.setup_mqtt()

    def setup_mqtt(self):
        """Set up MQTT client for receiving data."""
        client = mqtt.Client()
        client.on_message = self.on_message
        client.connect("broker.hivemq.com", 1883)
        client.subscribe("drone/data")
        client.loop_start()
        return client

    def on_message(self, client, userdata, message):
        """Callback function for receiving drone data."""
        received_data = json.loads(message.payload.decode())
        self.data.append(received_data)
        self.update_map()

    def update_map(self):
        """Update farm map with latest nitrogen deficiency data."""
        farm_map = folium.Map(location=[12.345, 67.890], zoom_start=15)
        
        for entry in self.data:
            lat, lon = entry["location"]["lat"], entry["location"]["lon"]
            status = entry["status"]
            color = "green" if status == "Healthy" else "orange" if status == "Mild Deficiency" else "red"
            
            folium.CircleMarker(
                location=[lat, lon],
                radius=10,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.7,
                popup=f"Status: {status}"
            ).add_to(farm_map)

        farm_map.save("farm_map.html")
        print("Map updated!")

    def run(self):
        """Keep application running."""
        print("Ground Application Running...")
        while True:
            pass  # Keep script alive

if __name__ == "__main__":
    app = GroundApplication()
    app.run()
