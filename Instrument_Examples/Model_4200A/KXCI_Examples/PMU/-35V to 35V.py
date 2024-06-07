'''
NOTE: THIS EXAMPLE PROGRAM REQUIRES CLARIUS VERSION 1.13 OR LATER!

This example creates a Segment Arb (SegARB) waveform sequence that outputs 35 V and then -35 V from a 4225-PMU with the 4225-RPMs.
This code uses ethernet to communicate to the 4200A. Two channels are used.
The timing sequences are specified in milliseconds, with a 100k load on both channels.
Device used: 100kohm resistor on channels 1 and 2, with channel 2 configured to measure the "low-side"
'''

from instrcomms import Communications
#Extra commands for plotting
import plotly.express as px
import pandas as pd
import time

INST_RESOURCE_STR = "TCPIP0::192.0.2.0::1225::SOCKET" # instrument resource string, obtained from NI MAX
my4200 = Communications(INST_RESOURCE_STR) # opens the resource manager in PyVISA with the corresponding instrument resource string
my4200.connect() # opens connections to the 4200A-SCS
my4200._instrument_object.write_termination = "\0" #Set PyVISA write terminator
my4200._instrument_object.read_termination = "\0" #Set PyVISA read terminator

my4200.query(":PMU:INIT 1") #Initialize PMU and set to SegARB mode

seq1 = 1

ch1 = 1
my4200.query(f":PMU:RPM:CONFIGURE PMU1-1, 0") #RPM output set to PMU channel 1
my4200.query(f":PMU:SOURCE:RANGE {ch1}, 40") #Set to 40V source and measure range
my4200.query(f":PMU:LOAD {ch1}, 100e3") #Set load to 100kohm
my4200.query(f":PMU:SARB:SEQ:TIME {ch1}, {seq1}, 10e-6, 10e-6, 1e-3, 10e-6, 1e-3, 10e-6, 1e-3, 10e-6, 10e-6") #Array of segment times (length in seconds) for ch1, sequence 1
my4200.query(f":PMU:SARB:SEQ:STARTV {ch1}, {seq1}, 0, 0, 35, 35, 0, 0, -35, -35, 0") #Array of starting voltages for ch1, sequence 1
my4200.query(f":PMU:SARB:SEQ:STOPV {ch1}, {seq1}, 0, 35, 35, 0, 0, -35, -35, 0, 0") #Array of stopping voltages for ch1, sequence 1

my4200.query(f":PMU:SARB:WFM:SEQ:LIST {ch1}, {seq1}, 1") #Sequence list (seq1) for channel 1 executing one time
my4200.query(f":PMU:OUTPUT:STATE {ch1}, 1") #Output state On

ch2 = 2
my4200.query(f":PMU:RPM:CONFIGURE PMU1-2, 0") #RPM output set to PMU channel 2
my4200.query(f":PMU:SOURCE:RANGE {ch2}, 40") #Set to 40V source and measure range
my4200.query(f":PMU:LOAD {ch2}, 100e3") #Set load to 100kohm
my4200.query(f":PMU:MEASURE:RANGE {ch2}, 2, 10e-3") #10mA fixed current range
my4200.query(f":PMU:SARB:SEQ:TIME {ch2}, {seq1}, 10e-6, 10e-6, 1e-3, 10e-6, 1e-3, 10e-6, 1e-3, 10e-6, 10e-6") #Array of segment times (length in seconds) for ch2, sequence 1
my4200.query(f":PMU:SARB:SEQ:STARTV {ch2}, {seq1}, 0, 0, 0, 0, 0, 0, 0, 0, 0") #Array of starting voltages for ch2, sequence 1
my4200.query(f":PMU:SARB:SEQ:STOPV {ch2}, {seq1}, 0, 0, 0, 0, 0, 0, 0, 0, 0") #Array of stopping voltages for ch2, sequence 1

#Configure measurements on ch2 only - perform waveform discrete measurements for each segment, starting the measurement at the beginning of the segment and stopping at the end
my4200.query(f":PMU:SARB:SEQ:MEAS:TYPE {ch2}, {seq1}, 2, 2, 2, 2, 2, 2, 2, 2, 2") #Array of measurement types for ch2, sequence 1 - perform waveform discrete measurement for each segment
my4200.query(f":PMU:SARB:SEQ:MEAS:START {ch2}, {seq1}, 0, 0, 0, 0, 0, 0, 0, 0, 0") #Array of measurement start times for ch2, sequence 1
my4200.query(f":PMU:SARB:SEQ:MEAS:STOP {ch2}, {seq1}, 10e-6, 10e-6, 1e-3, 10e-6, 1e-3, 10e-6, 1e-3, 10e-6, 10e-6") #Array of stop measure times

my4200.query(f":PMU:SARB:WFM:SEQ:LIST {ch2}, {seq1}, 1") #Sequence list (seq1) for channel 2 executing one time
my4200.query(f":PMU:OUTPUT:STATE {ch2}, 1") #Output state On

my4200.query(":PMU:EXECUTE") #Execute test

#This is a loop to check the status of the test
#The :PMU:TEST:STATUS? command returns 1 if it is still running and 0 if it is idle
while True:
    status = my4200.query(":PMU:TEST:STATUS?")
    
    #Continues loop until the test is complete
    #Casting the status string to int makes the comparison simpler since it ignores the termination characters
    if int(status) == 0:
        print("Measurement Complete.")
        break
    
    #Continously prints the status of the test every second to the terminal
    print(f"Status: {status}")
    time.sleep(1)

# Get the total number of data points for ch2
data_points_str = my4200.query(f":PMU:DATA:COUNT? {ch2}")
data_points = int(data_points_str)
print(f"Total data points for channel {ch2}: {data_points}")

# Initialize an empty DataFrame to store all data points
df_all_channels = pd.DataFrame(columns=['Voltage', 'Current', 'Timestamp', 'Status'])

# Loop through the data points in chunks
for start_point in range(0, data_points, 2048):
    # Get data for the current chunk
    response = my4200.query(f":PMU:DATA:GET {ch2}, {start_point}, 2048")

    # Split the response using semicolon as the delimiter for each point
    coords = response.split(";")

    # Split into 4 separate values for each point
    coords2d = [value.split(",") for value in coords]

    # Create a DataFrame for the current chunk
    df_chunk = pd.DataFrame(coords2d, columns=['Voltage', 'Current', 'Timestamp', 'Status'])

    # Concatenate the current chunk to the overall DataFrame
    df_all_channels = pd.concat([df_all_channels, df_chunk])

#Set the output state of both channels to off - always turn off the output at the end of a test
my4200.query(f":PMU:OUTPUT:STATE {ch1}, 0")
my4200.query(f":PMU:OUTPUT:STATE {ch2}, 0")

# Reset the index of the final DataFrame
df_all_channels.reset_index(drop=True, inplace=True)

# Print the combined DataFrame
print("Combined DataFrame: ", df_all_channels)

# Convert columns to appropriate types, floating point for the voltage and current, and a string for the timestamp and status
df_all_channels = df_all_channels.astype({'Voltage': float, 'Current': float, 'Timestamp': float, 'Status': str})

# Save DataFrame to a CSV file
df_all_channels.to_csv('data_table1.csv', index=False)
print("CSV file saved successfully.")  # Verify the data was saved

# Add a new column to the DataFrame with "Current" multiplied by -1
df_all_channels['Actual Current'] = df_all_channels['Current'] * -1

# Scatter plot with Voltage High and Current High on the plot, and all data in hover
fig = px.scatter(df_all_channels, x='Timestamp', y='Actual Current',
                 title='Current Response of 100kohm Resistor with +/- 35V Pulses using SegARB',
                 labels={'Timestamp': 'Time Output (s)', 'Actual Current': 'Current (A)'},
                 hover_data=["Timestamp", "Current"])

# Add a line trace
fig.add_trace(px.line(df_all_channels, x='Timestamp', y='Actual Current').data[0])

# Show the plot
fig.show()

my4200.disconnect()  # close communications with the 4200A-SCS
