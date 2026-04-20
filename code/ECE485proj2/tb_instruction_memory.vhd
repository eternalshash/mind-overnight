library IEEE;
use IEEE.STD_LOGIC_1164.ALL;

entity tb_instruction_memory is
-- Empty entity for test bench
end tb_instruction_memory;

architecture Behavioral of tb_instruction_memory is

    component instruction_memory
        Port ( read_addr : in  STD_LOGIC_VECTOR(31 downto 0);
               instr     : out STD_LOGIC_VECTOR(31 downto 0));
    end component;

    signal sig_read_addr : STD_LOGIC_VECTOR(31 downto 0) := (others => '0');
    signal sig_instr     : STD_LOGIC_VECTOR(31 downto 0);

begin

    UUT: instruction_memory port map (
        read_addr => sig_read_addr,
        instr     => sig_instr
    );

    stim_proc: process
    begin
        -- Give the system time to settle
        wait for 20 ns;

        -- TEST 1: Read Address 0
        -- Expected output: 20080005 (addi $t0, $zero, 5)
        sig_read_addr <= x"00000000";
        wait for 20 ns;

        -- TEST 2: Read Address 4
        -- Expected output: 2009000A (addi $t1, $zero, 10)
        sig_read_addr <= x"00000004";
        wait for 20 ns;

        -- TEST 3: Read Address 8
        -- Expected output: 01095020 (add $t2, $t0, $t1)
        sig_read_addr <= x"00000008";
        wait for 20 ns;

        -- End simulation
        wait;
    end process;


end Behavioral;