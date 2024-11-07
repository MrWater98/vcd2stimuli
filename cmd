yosys RocketTile.ys  > btor.log 2>&1
../../ponocca/build/pono --bound 500 --promote-inputvars -e bmc -p 0 --vcd cex.vcd RocketTile_dut.btor