from urllib.parse import urlparse
from app.ui import extract_ck_parameters, extract_ck_query

def test_parameter_matching():
	service = "some_service"
	user = "some_user"
	post_1 = "902183091283"
	post_2 = "129090sdadb0982"

	simple_profile = extract_ck_parameters(urlparse(f"https://coomer.su/{service}/user/{user}"))
	assert simple_profile[0] == service
	assert simple_profile[1] == user
	assert simple_profile[2] == None

	profile_search = extract_ck_parameters(urlparse(f"https://kemono.su/{service}/user/{user}?q=some_string"))
	assert profile_search[0] == service
	assert profile_search[1] == user
	assert profile_search[2] == None

	profile_post_1 = extract_ck_parameters(urlparse(f"https://somerandomwebsitethatlookslikekemono.su/{service}/user/{user}/post/{post_1}"))
	assert profile_post_1[0] == service
	assert profile_post_1[1] == user
	assert profile_post_1[2] == post_1

	profile_post_2 = extract_ck_parameters(urlparse(f"https://kemono.su/{service}/user/{user}/post/{post_2}"))
	assert profile_post_2[0] == service
	assert profile_post_2[1] == user
	assert profile_post_2[2] == post_2

def test_query_matching():
	search_1 = "my_search"
	result_1 = extract_ck_query(urlparse(f"https://kemono.su/alksdm/user/asdaf?q={search_1}"))
	assert result_1[0] == search_1
	assert result_1[1] == 0

	offset_2 = 10
	result_2 = extract_ck_query(urlparse(f"https://kemono.su/alksdm/user/asdaf?o={offset_2}"))
	assert result_2[0] == None
	assert result_2[1] == offset_2

	search_3 = "asdnalks"
	offset_3 = 0
	result_3 = extract_ck_query(urlparse(f"https://kemono.su/alksdm/user/asdaf?q={search_3}&o={offset_3}"))
	assert result_3[0] == search_3
	assert result_3[1] == offset_3

if __name__ == '__main__':
	test_parameter_matching()
	test_query_matching()
