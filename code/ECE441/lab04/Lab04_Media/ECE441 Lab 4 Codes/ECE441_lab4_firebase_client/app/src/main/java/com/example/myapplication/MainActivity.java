package com.example.myapplication;

import android.os.Bundle;
import android.util.Log;
import android.widget.TextView;

import androidx.activity.EdgeToEdge;
import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.graphics.Insets;
import androidx.core.view.ViewCompat;
import androidx.core.view.WindowInsetsCompat;

import com.google.firebase.FirebaseApp;
import com.google.firebase.database.DataSnapshot;
import com.google.firebase.database.DatabaseError;
import com.google.firebase.database.DatabaseReference;
import com.google.firebase.database.FirebaseDatabase;
import com.google.firebase.database.ValueEventListener;

import java.util.logging.Logger;

public class MainActivity extends AppCompatActivity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        FirebaseApp.initializeApp(this);
        EdgeToEdge.enable(this);
        setContentView(R.layout.activity_main);
        ViewCompat.setOnApplyWindowInsetsListener(findViewById(R.id.main), (v, insets) -> {
            Insets systemBars = insets.getInsets(WindowInsetsCompat.Type.systemBars());
            v.setPadding(systemBars.left, systemBars.top, systemBars.right, systemBars.bottom);
            return insets;
        });
        Thread thread = new Thread(){
            @Override
            public void run() {
                try {
                    basicReadWrite();
                } catch (Exception e) {
                    e.printStackTrace();
                }

                return;
            };
        };
        thread.start();

    }
    public void basicReadWrite() {
        FirebaseDatabase database = FirebaseDatabase.getInstance();
        DatabaseReference myFirebase = database.getReference("SensorDatabase");

        TextView timeUI=findViewById(R.id.text_time);
        TextView tempUI=findViewById(R.id.text_temp);
        TextView humidUI=findViewById(R.id.text_humid);

        myFirebase.addValueEventListener(new ValueEventListener() {
            @Override
            public void onDataChange(@NonNull DataSnapshot dataSnapshot) {
                String time_stamp = dataSnapshot.child("timestamp").getValue(String.class);
                String humidity = dataSnapshot.child("humidity").getValue(String.class);
                String temperature = dataSnapshot.child("temperature").getValue(String.class);
                Log.d("MainActivity", time_stamp + " Humidity: " + humidity + " Temperature: " + temperature);
                runOnUiThread(() -> {
                    // Stuff that updates the UI
                    timeUI.setText(time_stamp);
                    if (temperature == null) throw new AssertionError();
                    tempUI.setText(temperature.concat("°C"));
                    if (humidity == null) throw new AssertionError();
                    humidUI.setText(humidity.concat("%"));
                });

            }

            @Override
            public void onCancelled(@NonNull DatabaseError error) {
                Log.w("MainActivity", "Failed to read value.", error.toException());
            }
        });
    }
}