library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;

entity data_memory is
    Port ( clk        : in  STD_LOGIC;
           mem_write  : in  STD_LOGIC;
           mem_read   : in  STD_LOGIC;
           addr       : in  STD_LOGIC_VECTOR(31 downto 0);
           write_data : in  STD_LOGIC_VECTOR(31 downto 0);
           read_data  : out STD_LOGIC_VECTOR(31 downto 0));
end data_memory;

architecture Behavioral of data_memory is
    type ram_type is array (0 to 63) of STD_LOGIC_VECTOR(31 downto 0);
    signal ram : ram_type := (others => x"00000000");
begin
    process(clk)
    begin
        if rising_edge(clk) then
            if mem_write = '1' then
                ram(to_integer(unsigned(addr(7 downto 2)))) <= write_data;
            end if;
        end if;
    end process;

    read_data <= ram(to_integer(unsigned(addr(7 downto 2)))) when mem_read = '1' else x"00000000";
end Behavioral;

