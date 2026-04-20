library IEEE;
use IEEE.STD_LOGIC_1164.ALL;

entity tb_ece485 is
end tb_ece485;

architecture Behavioral of tb_ece485 is
    -- Signals to connect to the CPU ports
    signal clk   : std_logic := '0';
    signal reset : std_logic := '0';
    
    -- Clock period definition (100MHz clock)
    constant clk_period : time := 10 ns;

begin

    -- 1. Instantiate the Unit Under Test (UUT)
    -- This pulls the CPU from ece485.vhd
    UUT: entity work.mips_single_cycle 
        port map (
            clk   => clk,
            reset => reset
        );

    -- 2. Clock Generation Process
    -- Toggles the clock every 5ns
    clk_process : process
    begin
        clk <= '0';
        wait for clk_period/2;
        clk <= '1';
        wait for clk_period/2;
    end process;
    

    -- 3. Stimulus Process
    -- Drives the Reset and controls simulation length
    stim_proc: process
    begin		
        -- Step 1: Initialize with Reset
        reset <= '1';
        wait for 25 ns;	
        
        -- Step 2: Release Reset to start CPU execution
        reset <= '0';

        -- Step 3: Run for a set amount of time
        -- 100ns is enough to see the PC increment from 0 to 4, 8, 12, etc.
        wait for 100 ns;

        -- Step 4: Stop the simulation to prevent massive VCD files
        -- This 'wait' with no time value pauses the process indefinitely
        wait; 
    end process;

end Behavioral;
