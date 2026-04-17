library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;

entity tb_alu_32bit is
-- Test bench entities are always empty
end tb_alu_32bit;

architecture Behavioral of tb_alu_32bit is

    -- 1. Declare the component we are testing
    component alu_32bit
        Port ( a           : in  STD_LOGIC_VECTOR(31 downto 0);
               b           : in  STD_LOGIC_VECTOR(31 downto 0);
               alu_control : in  STD_LOGIC_VECTOR(3 downto 0);
               alu_result  : out STD_LOGIC_VECTOR(31 downto 0);
               zero_flag   : out STD_LOGIC);
    end component;

    -- 2. Declare internal signals to wire to the component
    signal sig_a           : STD_LOGIC_VECTOR(31 downto 0) := (others => '0');
    signal sig_b           : STD_LOGIC_VECTOR(31 downto 0) := (others => '0');
    signal sig_alu_control : STD_LOGIC_VECTOR(3 downto 0)  := (others => '0');
    signal sig_result      : STD_LOGIC_VECTOR(31 downto 0);
    signal sig_zero        : STD_LOGIC;

begin

    -- 3. Instantiate the ALU and map the ports
    UUT: alu_32bit port map (
        a           => sig_a,
        b           => sig_b,
        alu_control => sig_alu_control,
        alu_result  => sig_result,
        zero_flag   => sig_zero
    );

    -- 4. The Stimulus Process (Feeding data to the ALU)
    stim_proc: process
    begin
        -- Give the system 20ns to settle
        wait for 20 ns;	

        -- TEST 1: ADD (0010)
        -- a = 15, b = 10. Expected Result: 25 (Hex: 19), Zero = 0
        sig_a <= x"0000000F"; 
        sig_b <= x"0000000A";
        sig_alu_control <= "0010";
        wait for 20 ns;

        -- TEST 2: SUBTRACT (0110) & ZERO FLAG TEST
        -- a = 25, b = 25. Expected Result: 0 (Hex: 00), Zero = 1
        sig_a <= x"00000019"; 
        sig_b <= x"00000019";
        sig_alu_control <= "0110";
        wait for 20 ns;

        -- TEST 3: BITWISE AND (0000)
        -- a = ...1111, b = ...1010. Expected Result: ...1010 (Hex: 0A)
        sig_a <= x"0000000F"; 
        sig_b <= x"0000000A";
        sig_alu_control <= "0000";
        wait for 20 ns;

        -- TEST 4: SET ON LESS THAN (0111)
        -- a = 5, b = 10. Expected Result: 1 (Because 5 < 10)
        sig_a <= x"00000005"; 
        sig_b <= x"0000000A";
        sig_alu_control <= "0111";
        wait for 20 ns;

        -- End simulation
        wait;
    end process;

end Behavioral;