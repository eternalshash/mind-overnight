library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;

entity instruction_memory is
    Port ( read_addr : in  STD_LOGIC_VECTOR(31 downto 0);
           instr     : out STD_LOGIC_VECTOR(31 downto 0));
end instruction_memory;

architecture Behavioral of instruction_memory is
    type rom_type is array (0 to 15) of STD_LOGIC_VECTOR(31 downto 0);
    constant ROM : rom_type := (
        0 => x"8E4B012C", -- PC = 0:  lw  $t3, 300($s2)
        1 => x"AEEE0190", -- PC = 4:  sw  $t6, 400($s7)
        2 => x"01716820", -- PC = 8:  add $t5, $t3, $s1
        3 => x"12CD00C8", -- PC = 12: bne $s6, $t5, 200
        others => x"00000000"
    );
begin
    -- Divide address by 4 to get the correct array index
    instr <= ROM(to_integer(unsigned(read_addr(5 downto 2)))) when unsigned(read_addr) < 64 else x"00000000";
end Behavioral;