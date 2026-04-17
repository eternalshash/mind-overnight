library IEEE;
use IEEE.STD_LOGIC_1164.ALL;

entity pc_register is
    Port ( clk      : in  STD_LOGIC;
           reset    : in  STD_LOGIC;
           pc_in    : in  STD_LOGIC_VECTOR(31 downto 0);
           pc_out   : out STD_LOGIC_VECTOR(31 downto 0));
end pc_register;

architecture Behavioral of pc_register is
begin
    process(clk, reset)
    begin
        -- Asynchronous reset: Immediately jumps to address 0
        if reset = '1' then
            pc_out <= x"00000000";
            
        -- Synchronous update: Only on the rising edge of the clock
        elsif rising_edge(clk) then
            pc_out <= pc_in;
        end if;
    end process;
end Behavioral;

