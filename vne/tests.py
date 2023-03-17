import gbl
from substrate import SubstrateHost
import numpy as np


#########################################################################################

# TESTING FUNCTIONS: ping, iperf and cpu limit tests.


def test_ping_within_vnr_vhosts(net):
    """ Test ping between every virtual host in each VNR separately."""
    for vnr in gbl.MAPPED_VNRS:
        print("\nChecking ping for vnr{}...".format(vnr.vnr_number))
        vhosts = [net[vh.name] for vh in vnr.virtual_hosts]
        ping_results = net.pingFull(hosts=vhosts)
        bool_failed_pings = False
        for ping_result in ping_results:
            if ping_result[2][1] != ping_result[2][0]:
                print(
                    gbl.bcolors.FAIL + "Ping test FAILED for VNR {}!".format(vnr.vnr_number) + gbl.bcolors.ENDC)
                bool_failed_pings = True
        if not bool_failed_pings:
            print(gbl.bcolors.OKGREEN +
                  "Ping test PASSED for VNR {}!".format(vnr.vnr_number) + gbl.bcolors.ENDC)


def test_iperf_bandwidth_within_vnr_vhosts(net):
    """ Test iperf to check link bandwidth for all the virtual links as provided in each VNR."""
    for vnr in gbl.MAPPED_VNRS:
        print("\nChecking iperf bandwidths for links in vnr{}...".format(
            vnr.vnr_number))
        bool_failed_iperf = False
        for link in vnr.vnr_links_with_bw:
            h1_name, h2_name, bw_expected = link[0], link[1], link[2]
            vh1 = vnr.hostname_x_vh[h1_name]
            vh2 = vnr.hostname_x_vh[h2_name]
            iperf_result = net.iperf(hosts=[net[vh1.name], net[vh2.name]])
            # We are mainly interested in verifying the lower limit, i.e. iperf_result[0]
            # because we have to ensure its sufficient as per the expected bandwidth.
            # Iperf uses the unit `Mbits`, whereas traffic control commands use the unit `mbits`.
            # The conversion factor is 1 Mbit = 1.024 * 1.024 mbit.
            bw_obtained = float(iperf_result[0].split(" ")[0]) * 1.024 * 1.024
            if iperf_result[0].split(" ")[1] == "Kbits/sec":
                bw_obtained = (bw_obtained / 1000) * 1.024
            # Computing MAPE (mean absolute percentage error).
            mean_absolute_percentage_error = np.mean(
                np.abs((bw_expected - bw_obtained)/bw_expected))*100
            # Imposing threshold condition for how much MAPE to allow. Can be changed.
            if mean_absolute_percentage_error > 5.0:
                print(gbl.bcolors.FAIL + "Iperf test FAILED for VNR {}, MAPE = {}, bw_expected = {}, bw_obtained = {}.".format(
                    vnr.vnr_number, mean_absolute_percentage_error, bw_expected, bw_obtained) + gbl.bcolors.ENDC)
                bool_failed_iperf = True
        if not bool_failed_iperf:
            print(gbl.bcolors.OKGREEN +
                  "Iperf test PASSED for VNR {}!".format(vnr.vnr_number) + gbl.bcolors.ENDC)

#########################################################################################

# CPU LIMIT RELATED FUNCTIONS


def test_cpu_limits_for_all_hosts(net, duration=5):
    """ Test cpu limit for all hosts in the network."""
    print("\n\n====================== Runnnig CPU limit test =========================")
    cpu_result = net.runCpuLimitTest(cpu=1, duration=duration)
    ind = 0
    for h in net.hosts:
        sum = 0
        for _ in range(duration):
            sum += cpu_result[ind]
            ind += 1
        cpu_expected = gbl.HOSTNAME_x_HOST[str(h)].cpu_limit
        cpu_observed = sum/duration * SubstrateHost.cpu_all_hosts / 100
        # Computing MAPE (mean absolute percentage error).
        mean_absolute_percentage_error = np.mean(
            np.abs((cpu_expected - cpu_observed)/cpu_expected))*100
        # Imposing threshold condition for how much MAPE to allow. Can be changed.
        if mean_absolute_percentage_error > 10.0:
            print(gbl.bcolors.FAIL + "CPU limit test FAILED for host {}, MAPE = {}, cpu_expected = {}, cpu_observed = {}.".format(
                h, f'{mean_absolute_percentage_error:.4f}', f'{cpu_expected:.4f}', f'{cpu_observed:.4f}') + gbl.bcolors.ENDC)
        else:
            print(gbl.bcolors.OKGREEN + "CPU limit test PASSED for host {}, MAPE = {}, cpu_expected = {}, cpu_observed = {}.".format(
                h, f'{mean_absolute_percentage_error:.4f}', f'{cpu_expected:.4f}', f'{cpu_observed:.4f}') + gbl.bcolors.ENDC)
    print("=======================================================================")

#########################################################################################
