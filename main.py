from scripts.cbsim import OSM_download, net, net_draw

N = net.Net()


N.bbox = net.AreaBoundingBox(longitude_west=19.9300, longitude_east=19.94537, latitude_south=50.05395,
                                      latitude_north=50.06631)


N = OSM_download.generate_network(net = N,simplify=True, simplify_tolerance=10,draw_network=True)

net_draw.draw_results(N)


