import ruddr

# TODO NOTES: Some of these tests involve the manager as well. In some cases
#   (e.g. update same address currently assigned) we can mock the manager and
#   just provide the addrfile functions. Others are meant to test the actual
#   manager's addrfile functionality (e.g. update same address after restart
#   manager). Arguably, this second type of test should go in test_manager.py.

# TODO test basic updates

# TODO test update same address currently assigned
#  (should not happen)

# TODO test update same address currently assigned after failed update
#  (should happen)

# TODO test update same address currently assigned after restart manager
#  (should not happen)

# TODO test update different address after restart manager (should happen)

# TODO test update same address currently assigned after failed update followed
#  by restart manager (should happen)

# TODO test update retries after failed update, and does not retry again

# TODO test update does not retry after failed update then additional successful
#  update
